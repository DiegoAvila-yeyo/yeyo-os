/**
 * Tests para Notifications — Micro-fase 3.9
 */

import { render, screen, fireEvent, act } from '@testing-library/react';
import Notifications from '@/components/common/Notifications';
import {
  useNotificationStore,
  MAX_VISIBLE,
  AUTO_DISMISS_MS,
} from '@/lib/store/notification-store';

describe('Notification System', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    act(() => {
      useNotificationStore.setState({ notifications: [] });
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('NotificationStore', () => {
    it('agrega una notificacion', () => {
      act(() => {
        useNotificationStore.getState().addNotification('info', 'Test message');
      });
      expect(useNotificationStore.getState().notifications).toHaveLength(1);
    });

    it('retorna el id de la notificacion', () => {
      let id = '';
      act(() => {
        id = useNotificationStore.getState().addNotification('success', 'Done');
      });
      expect(id).toMatch(/^notif-/);
    });

    it('la notificacion tiene todas las propiedades', () => {
      let id = '';
      act(() => {
        id = useNotificationStore.getState().addNotification('warning', 'Watch out', false);
      });
      const notif = useNotificationStore.getState().notifications[0];
      expect(notif.id).toBe(id);
      expect(notif.type).toBe('warning');
      expect(notif.message).toBe('Watch out');
      expect(notif.autoDismiss).toBe(false);
      expect(notif.createdAt).toBeGreaterThan(0);
    });

    it('limita a MAX_VISIBLE notificaciones', () => {
      act(() => {
        for (let i = 0; i < MAX_VISIBLE + 3; i++) {
          useNotificationStore.getState().addNotification('info', `msg ${i}`, false);
        }
      });
      expect(useNotificationStore.getState().notifications.length).toBeLessThanOrEqual(MAX_VISIBLE);
    });

    it('mantiene las mas recientes al superar el limite', () => {
      act(() => {
        for (let i = 0; i < MAX_VISIBLE + 2; i++) {
          useNotificationStore.getState().addNotification('info', `msg ${i}`, false);
        }
      });
      const msgs = useNotificationStore.getState().notifications.map((n) => n.message);
      expect(msgs).toContain(`msg ${MAX_VISIBLE + 1}`);
      expect(msgs).not.toContain('msg 0');
    });

    it('removeNotification elimina por id', () => {
      let id = '';
      act(() => {
        id = useNotificationStore.getState().addNotification('error', 'Error', false);
      });
      act(() => {
        useNotificationStore.getState().removeNotification(id);
      });
      expect(useNotificationStore.getState().notifications).toHaveLength(0);
    });

    it('removeNotification no afecta otras notificaciones', () => {
      let id1 = '', id2 = '';
      act(() => {
        id1 = useNotificationStore.getState().addNotification('info', 'a', false);
        id2 = useNotificationStore.getState().addNotification('error', 'b', false);
      });
      act(() => {
        useNotificationStore.getState().removeNotification(id1);
      });
      const remaining = useNotificationStore.getState().notifications;
      expect(remaining).toHaveLength(1);
      expect(remaining[0].id).toBe(id2);
    });

    it('auto-dismiss despues de AUTO_DISMISS_MS', () => {
      act(() => {
        useNotificationStore.getState().addNotification('info', 'Auto dismiss');
      });
      expect(useNotificationStore.getState().notifications).toHaveLength(1);
      act(() => {
        jest.advanceTimersByTime(AUTO_DISMISS_MS + 100);
      });
      expect(useNotificationStore.getState().notifications).toHaveLength(0);
    });

    it('no auto-dismiss cuando autoDismiss=false', () => {
      act(() => {
        useNotificationStore.getState().addNotification('info', 'Persiste', false);
      });
      act(() => {
        jest.advanceTimersByTime(AUTO_DISMISS_MS + 100);
      });
      expect(useNotificationStore.getState().notifications).toHaveLength(1);
    });

    it('clearAll vacia todas las notificaciones', () => {
      act(() => {
        useNotificationStore.getState().addNotification('info', 'a', false);
        useNotificationStore.getState().addNotification('error', 'b', false);
        useNotificationStore.getState().clearAll();
      });
      expect(useNotificationStore.getState().notifications).toHaveLength(0);
    });
  });

  describe('Notifications Component', () => {
    it('no renderiza cuando no hay notificaciones', () => {
      render(<Notifications />);
      expect(screen.queryByTestId('notification-stack')).not.toBeInTheDocument();
    });

    it('renderiza notificaciones del store', () => {
      act(() => {
        useNotificationStore.getState().addNotification('info', 'Hello', false);
      });
      render(<Notifications />);
      expect(screen.getByTestId('notification-stack')).toBeInTheDocument();
      expect(screen.getByText('Hello')).toBeInTheDocument();
    });

    it('cada tipo tiene el data-type correcto', () => {
      let id = '';
      act(() => {
        id = useNotificationStore.getState().addNotification('error', 'Error msg', false);
      });
      render(<Notifications />);
      const notif = screen.getByTestId(`notification-${id}`);
      expect(notif.dataset.type).toBe('error');
    });

    it('boton cerrar remueve la notificacion', () => {
      let id = '';
      act(() => {
        id = useNotificationStore.getState().addNotification('warning', 'Warn', false);
      });
      render(<Notifications />);
      fireEvent.click(screen.getByTestId(`close-${id}`));
      expect(useNotificationStore.getState().notifications).toHaveLength(0);
    });

    it('muestra multiples notificaciones', () => {
      act(() => {
        useNotificationStore.getState().addNotification('info', 'First', false);
        useNotificationStore.getState().addNotification('success', 'Second', false);
        useNotificationStore.getState().addNotification('error', 'Third', false);
      });
      render(<Notifications />);
      expect(screen.getByText('First')).toBeInTheDocument();
      expect(screen.getByText('Second')).toBeInTheDocument();
      expect(screen.getByText('Third')).toBeInTheDocument();
    });
  });

  describe('constantes', () => {
    it('MAX_VISIBLE es 5', () => {
      expect(MAX_VISIBLE).toBe(5);
    });

    it('AUTO_DISMISS_MS es 5000', () => {
      expect(AUTO_DISMISS_MS).toBe(5000);
    });
  });
});
