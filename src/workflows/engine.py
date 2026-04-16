"""
YeyoOS — Workflow Execution Engine
Micro-fase 3.20 — Capa 4: Orchestration

Sequential engine that walks the workflow node graph, executing
registered handlers for each NodeType.  Supports conditions, loops,
delays, per-node timeouts, retries, variable resolution, and
real-time WebSocket progress broadcasting.
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from src.workflows.models import (
    ExecutionStatus,
    NodeExecutionResult,
    NodeType,
    Workflow,
    WorkflowExecution,
    WorkflowNode,
)

logger = logging.getLogger("yeyoos.workflows.engine")

NODE_TIMEOUT: int = 300  # 5 minutes per node
MAX_RETRIES: int = 1


class WorkflowEngine:
    """Orchestrates sequential execution of workflow nodes.

    Maintains a registry of handler callables (one per NodeType), tracks
    active executions, and pushes real-time progress over WebSocket.
    """

    def __init__(self) -> None:
        """Initialise engine state."""
        self._handlers: dict[NodeType, Callable] = {}
        self._executions: list[WorkflowExecution] = []
        self._ws_connections: dict[str, list[Any]] = {}

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(self, node_type: NodeType, handler: Callable) -> None:
        """Register a handler function for a specific node type.

        Args:
            node_type: The NodeType this handler services.
            handler:   An async callable ``(config, variables) -> dict``.
        """
        self._handlers[node_type] = handler
        logger.debug("Registered handler for %s", node_type.value)

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute(
        self, workflow: Workflow, variables: dict | None = None
    ) -> WorkflowExecution:
        """Execute a workflow from its entry node to completion.

        Walks the node graph sequentially following edges.  Special
        control-flow nodes (CONDITION, LOOP, DELAY) are handled inline.

        Args:
            workflow:  The Workflow definition to execute.
            variables: Optional initial variables merged with workflow defaults.

        Returns:
            A populated WorkflowExecution with results for every node.
        """
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status=ExecutionStatus.RUNNING,
            total_nodes=len(workflow.nodes),
            variables={**workflow.variables, **(variables or {})},
            started_at=datetime.now(timezone.utc),
        )
        self._executions.append(execution)
        logger.info(
            "Starting execution %s for workflow '%s' (%d nodes)",
            execution.id,
            workflow.name,
            execution.total_nodes,
        )

        try:
            current_node = workflow.get_entry_node()
            if current_node is None:
                raise RuntimeError("Workflow has no entry node")

            while current_node is not None:
                # Abort early if execution was cancelled externally
                if execution.status == ExecutionStatus.CANCELLED:
                    logger.info("Execution %s cancelled", execution.id)
                    break

                result = await self._execute_node(
                    current_node, workflow, execution
                )
                execution.node_results.append(result)
                execution.current_node_index += 1
                await self.broadcast_progress(execution)

                if result.status == ExecutionStatus.FAILED:
                    execution.status = ExecutionStatus.FAILED
                    execution.error = result.error
                    break

                # Determine the next node to visit
                current_node = self._resolve_next_node(
                    current_node, result, workflow, execution
                )

            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.COMPLETED

        except Exception as exc:
            logger.exception("Execution %s failed: %s", execution.id, exc)
            execution.status = ExecutionStatus.FAILED
            execution.error = str(exc)

        execution.completed_at = datetime.now(timezone.utc)
        await self.broadcast_progress(execution)
        logger.info(
            "Execution %s finished — %s", execution.id, execution.status.value
        )
        return execution

    # ------------------------------------------------------------------
    # Internal: single-node execution (with timeout + retry)
    # ------------------------------------------------------------------

    async def _execute_node(
        self,
        node: WorkflowNode,
        workflow: Workflow,
        execution: WorkflowExecution,
    ) -> NodeExecutionResult:
        """Execute a single node with timeout and retry logic.

        Args:
            node:      The WorkflowNode to execute.
            workflow:  Parent workflow (used for sub-graph traversal).
            execution: Active WorkflowExecution for variable context.

        Returns:
            NodeExecutionResult capturing output, timing, and status.
        """
        result = NodeExecutionResult(
            node_id=node.id,
            node_type=node.node_type,
            started_at=datetime.now(timezone.utc),
        )
        resolved_config = self.resolve_variables(node.config, execution.variables)

        for attempt in range(1 + MAX_RETRIES):
            start = time.monotonic()
            try:
                output = await asyncio.wait_for(
                    self._dispatch_node(node, resolved_config, workflow, execution),
                    timeout=NODE_TIMEOUT,
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                result.status = ExecutionStatus.COMPLETED
                result.output = output
                result.duration_ms = elapsed_ms
                result.completed_at = datetime.now(timezone.utc)
                result.retry_count = attempt

                # Merge handler output into execution variables when dict
                if isinstance(output, dict):
                    execution.variables.update(output)

                logger.debug(
                    "Node %s (%s) completed in %.1f ms",
                    node.id,
                    node.node_type.value,
                    elapsed_ms,
                )
                return result

            except asyncio.TimeoutError:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.warning(
                    "Node %s timed out after %.0f ms (attempt %d)",
                    node.id,
                    elapsed_ms,
                    attempt + 1,
                )
                result.error = f"Timeout after {NODE_TIMEOUT}s"
                result.duration_ms = elapsed_ms
                result.retry_count = attempt

            except Exception as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.warning(
                    "Node %s failed (attempt %d): %s",
                    node.id,
                    attempt + 1,
                    exc,
                )
                result.error = str(exc)
                result.duration_ms = elapsed_ms
                result.retry_count = attempt

        # All attempts exhausted
        result.status = ExecutionStatus.FAILED
        result.completed_at = datetime.now(timezone.utc)
        return result

    # ------------------------------------------------------------------
    # Internal: dispatch to handler or built-in logic
    # ------------------------------------------------------------------

    async def _dispatch_node(
        self,
        node: WorkflowNode,
        config: dict,
        workflow: Workflow,
        execution: WorkflowExecution,
    ) -> Any:
        """Route a node to the correct handler or built-in logic.

        CONDITION, LOOP, and DELAY nodes are handled directly by the
        engine.  All other types are forwarded to registered handlers.

        Returns:
            The output produced by the handler / built-in logic.
        """
        if node.node_type == NodeType.DELAY:
            seconds = config.get("seconds", 1)
            logger.debug("DELAY node %s — sleeping %s s", node.id, seconds)
            await asyncio.sleep(float(seconds))
            return {"delayed": seconds}

        if node.node_type == NodeType.CONDITION:
            return self._evaluate_condition(config, execution.variables)

        if node.node_type == NodeType.LOOP:
            return await self._execute_loop(node, config, workflow, execution)

        handler = self._handlers.get(node.node_type)
        if handler is None:
            raise RuntimeError(
                f"No handler registered for node type '{node.node_type.value}'"
            )
        return await handler(config, execution.variables)

    # ------------------------------------------------------------------
    # Built-in: condition evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_condition(config: dict, variables: dict) -> dict:
        """Evaluate a condition expression against current variables.

        The expression is evaluated with *variables* as the local
        namespace.  Only simple, read-only expressions should be used.

        Returns:
            ``{"result": True/False}`` so the caller can branch.
        """
        expression = config.get("expression", "False")
        try:
            import ast as _ast
            import operator

            _SAFE_OPS = {
                _ast.Eq: operator.eq,
                _ast.NotEq: operator.ne,
                _ast.Lt: operator.lt,
                _ast.LtE: operator.le,
                _ast.Gt: operator.gt,
                _ast.GtE: operator.ge,
                _ast.And: lambda a, b: a and b,
                _ast.Or: lambda a, b: a or b,
                _ast.Not: operator.not_,
                _ast.Is: operator.is_,
                _ast.IsNot: operator.is_not,
                _ast.In: lambda a, b: a in b,
                _ast.NotIn: lambda a, b: a not in b,
                _ast.Add: operator.add,
                _ast.Sub: operator.sub,
                _ast.Mult: operator.mul,
            }

            def _safe_eval(node: _ast.AST) -> Any:
                if isinstance(node, _ast.Expression):
                    return _safe_eval(node.body)
                if isinstance(node, _ast.Constant):
                    return node.value
                if isinstance(node, _ast.Name):
                    if node.id in variables:
                        return variables[node.id]
                    raise NameError(f"Undefined variable: {node.id}")
                if isinstance(node, _ast.Compare):
                    left = _safe_eval(node.left)
                    for op, comparator in zip(node.ops, node.comparators):
                        right = _safe_eval(comparator)
                        fn = _SAFE_OPS.get(type(op))
                        if fn is None:
                            raise ValueError(f"Unsupported operator: {type(op).__name__}")
                        if not fn(left, right):
                            return False
                        left = right
                    return True
                if isinstance(node, _ast.BoolOp):
                    values = [_safe_eval(v) for v in node.values]
                    fn = _SAFE_OPS[type(node.op)]
                    result = values[0]
                    for v in values[1:]:
                        result = fn(result, v)
                    return result
                if isinstance(node, _ast.UnaryOp) and isinstance(node.op, _ast.Not):
                    return not _safe_eval(node.operand)
                if isinstance(node, _ast.BinOp):
                    fn = _SAFE_OPS.get(type(node.op))
                    if fn is None:
                        raise ValueError(f"Unsupported binary op: {type(node.op).__name__}")
                    return fn(_safe_eval(node.left), _safe_eval(node.right))
                raise ValueError(f"Unsupported expression node: {type(node).__name__}")

            tree = _ast.parse(expression, mode="eval")
            result = bool(_safe_eval(tree))
        except Exception as exc:
            logger.warning("Condition eval failed (%s): %s", expression, exc)
            result = False
        return {"result": result}

    # ------------------------------------------------------------------
    # Built-in: loop execution
    # ------------------------------------------------------------------

    async def _execute_loop(
        self,
        node: WorkflowNode,
        config: dict,
        workflow: Workflow,
        execution: WorkflowExecution,
    ) -> dict:
        """Execute loop body nodes for the configured number of iterations.

        Args:
            node:      The LOOP WorkflowNode.
            config:    Resolved node config.
            workflow:  Parent workflow for node lookups.
            execution: Active execution context.

        Returns:
            Summary dict with iteration count and collected results.
        """
        loop_count = config.get("loop_count", node.loop_count)
        body_ids = config.get("loop_body", node.loop_body)
        results: list[Any] = []

        for i in range(max(0, int(loop_count))):
            execution.variables["loop_index"] = i
            for body_id in body_ids:
                body_node = workflow.get_node_by_id(body_id)
                if body_node is None:
                    logger.warning("Loop body node %s not found", body_id)
                    continue
                body_result = await self._execute_node(
                    body_node, workflow, execution
                )
                execution.node_results.append(body_result)
                execution.current_node_index += 1
                await self.broadcast_progress(execution)
                if body_result.status == ExecutionStatus.FAILED:
                    return {"iterations": i, "results": results, "error": body_result.error}
                results.append(body_result.output)

        return {"iterations": max(0, int(loop_count)), "results": results}

    # ------------------------------------------------------------------
    # Internal: next-node resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_next_node(
        current: WorkflowNode,
        result: NodeExecutionResult,
        workflow: Workflow,
        execution: WorkflowExecution,
    ) -> Optional[WorkflowNode]:
        """Determine the next node after *current* has executed.

        For CONDITION nodes the ``true_branch`` / ``false_branch`` is
        used.  For all others the first node from ``get_next_nodes`` is
        followed (sequential walk).
        """
        if current.node_type == NodeType.CONDITION:
            condition_result = (
                result.output.get("result", False) if isinstance(result.output, dict) else False
            )
            branch_id = current.true_branch if condition_result else current.false_branch
            if branch_id:
                return workflow.get_node_by_id(branch_id)
            return None

        next_nodes = workflow.get_next_nodes(current.id)
        return next_nodes[0] if next_nodes else None

    # ------------------------------------------------------------------
    # Variable resolution
    # ------------------------------------------------------------------

    def resolve_variables(self, config: dict, variables: dict) -> dict:
        """Deep-replace ``{var_name}`` patterns in config values.

        Recursively walks dicts and lists, substituting ``{key}``
        placeholders in string values with the corresponding entry
        from *variables*.

        Args:
            config:    Node configuration dict.
            variables: Current execution variables.

        Returns:
            A new dict with all placeholders resolved.
        """
        return self._resolve_value(config, variables)

    def _resolve_value(self, value: Any, variables: dict) -> Any:
        """Recursively resolve placeholders in an arbitrary value."""
        if isinstance(value, str):
            return re.sub(
                r"\{(\w+)\}",
                lambda m: str(variables.get(m.group(1), m.group(0))),
                value,
            )
        if isinstance(value, dict):
            return {k: self._resolve_value(v, variables) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(item, variables) for item in value]
        return value

    # ------------------------------------------------------------------
    # WebSocket progress broadcasting
    # ------------------------------------------------------------------

    async def broadcast_progress(self, execution: WorkflowExecution) -> None:
        """Send execution progress as JSON to all connected WebSockets.

        Args:
            execution: The current WorkflowExecution to serialise.
        """
        connections = self._ws_connections.get(execution.id, [])
        if not connections:
            return

        payload = json.dumps(execution.to_dict())
        stale: list[Any] = []
        for ws in connections:
            try:
                await ws.send(payload)
            except Exception:
                logger.debug("Removing stale WS for execution %s", execution.id)
                stale.append(ws)
        for ws in stale:
            connections.remove(ws)

    def add_ws_connection(self, exec_id: str, ws: Any) -> None:
        """Register a WebSocket connection for execution progress.

        Args:
            exec_id: The execution ID to subscribe to.
            ws:      A WebSocket-like object with an async ``send`` method.
        """
        self._ws_connections.setdefault(exec_id, []).append(ws)
        logger.debug("WS connected for execution %s", exec_id)

    def remove_ws_connection(self, exec_id: str, ws: Any) -> None:
        """Unregister a WebSocket connection.

        Args:
            exec_id: The execution ID to unsubscribe from.
            ws:      The WebSocket instance to remove.
        """
        conns = self._ws_connections.get(exec_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._ws_connections.pop(exec_id, None)
        logger.debug("WS disconnected for execution %s", exec_id)

    # ------------------------------------------------------------------
    # Execution queries
    # ------------------------------------------------------------------

    def get_execution(self, exec_id: str) -> Optional[WorkflowExecution]:
        """Retrieve an execution by its ID.

        Args:
            exec_id: Unique execution identifier.

        Returns:
            The matching WorkflowExecution or None.
        """
        for ex in self._executions:
            if ex.id == exec_id:
                return ex
        return None

    def get_executions_for_workflow(
        self, workflow_id: str
    ) -> list[WorkflowExecution]:
        """Return all executions belonging to a workflow.

        Args:
            workflow_id: The parent workflow ID.

        Returns:
            List of WorkflowExecution instances (may be empty).
        """
        return [ex for ex in self._executions if ex.workflow_id == workflow_id]

    def cancel_execution(self, exec_id: str) -> bool:
        """Mark an execution as cancelled.

        The running loop in ``execute()`` checks this flag before
        processing the next node and will stop gracefully.

        Args:
            exec_id: The execution ID to cancel.

        Returns:
            True if the execution was found and cancelled, False otherwise.
        """
        execution = self.get_execution(exec_id)
        if execution is None:
            return False
        if execution.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ):
            return False
        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)
        logger.info("Execution %s cancelled", exec_id)
        return True
