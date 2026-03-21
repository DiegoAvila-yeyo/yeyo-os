## ═══════════════════════════════════════
## MICRO-FASE 7.5 — YEYO Store Frontend
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.5-1 [VSCODE] — Crear UI del Store en el Neural Hub

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.5 de Capa 7 (Evolución): crear el frontend del YEYO Store integrado en el Neural Hub.

CONTEXTO:
- Micro-fases 7.3-7.4 completadas: Store Server y Security Pipeline creados
- El Neural Hub es la UI principal de YeyoOS (React + TypeScript)
- Store Frontend se integra como un nodo/vista dentro del Neural Hub
- Funcionalidades: búsqueda, categorías, featured, instalación con diálogo de permisos, reviews
- Developer dashboard para gestión de paquetes
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p frontend/src/components/store
   mkdir -p frontend/src/services
   mkdir -p frontend/src/__tests__/store

2. Crear archivo frontend/src/services/storeApi.ts:

   Ruta: ~/yeyo-os/frontend/src/services/storeApi.ts
   Contenido:

   /**
    * YeyoOS — Store API Client
    * Micro-fase 7.5 — Capa 7: Evolución
    */

   const STORE_API_BASE = '/api/store';

   export interface PackageManifest {
     name: string;
     version: string;
     description: string;
     author: string;
     permissions: string[];
     category: string;
     tags: string[];
     license: string;
   }

   export interface StorePackage {
     package_id: string;
     manifest: PackageManifest;
     developer_id: string;
     status: string;
     security_score: number | null;
     download_count: number;
     avg_rating: number;
     total_reviews: number;
     published_at: string | null;
   }

   export interface PackageReview {
     review_id: string;
     package_id: string;
     user_id: string;
     rating: number;
     comment: string;
     created_at: string;
   }

   export interface SearchResult {
     packages: StorePackage[];
     total: number;
     page: number;
     per_page: number;
   }

   export async function searchPackages(
     query?: string,
     category?: string,
     page: number = 1,
   ): Promise<SearchResult> {
     const params = new URLSearchParams();
     if (query) params.set('search', query);
     if (category) params.set('category', category);
     params.set('page', String(page));
     const resp = await fetch(`${STORE_API_BASE}/packages?${params}`);
     if (!resp.ok) throw new Error(`Store API error: ${resp.status}`);
     return resp.json();
   }

   export async function getPackage(packageId: string): Promise<StorePackage> {
     const resp = await fetch(`${STORE_API_BASE}/packages/${packageId}`);
     if (!resp.ok) throw new Error(`Package not found: ${packageId}`);
     return resp.json();
   }

   export async function getReviews(packageId: string): Promise<PackageReview[]> {
     const resp = await fetch(`${STORE_API_BASE}/packages/${packageId}/reviews`);
     if (!resp.ok) throw new Error(`Reviews error: ${resp.status}`);
     return resp.json();
   }

   export async function submitReview(
     packageId: string,
     rating: number,
     comment: string,
     userId: string,
   ): Promise<PackageReview> {
     const resp = await fetch(`${STORE_API_BASE}/packages/${packageId}/review`, {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ package_id: packageId, user_id: userId, rating, comment }),
     });
     if (!resp.ok) throw new Error(`Review submit error: ${resp.status}`);
     return resp.json();
   }

   export async function installPackage(packageId: string): Promise<void> {
     const resp = await fetch(`${STORE_API_BASE}/packages/${packageId}/install`, {
       method: 'POST',
     });
     if (!resp.ok) throw new Error(`Install error: ${resp.status}`);
   }

3. Crear archivo frontend/src/components/store/StoreNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/store/StoreNode.tsx
   Contenido:

   /**
    * YeyoOS — Store Node (Neural Hub)
    * Micro-fase 7.5 — Capa 7: Evolución
    *
    * Vista principal del YEYO Store dentro del Neural Hub.
    */

   import React, { useState, useEffect, useCallback } from 'react';
   import { searchPackages, StorePackage, SearchResult } from '../../services/storeApi';
   import PackageCard from './PackageCard';
   import PackageDetail from './PackageDetail';
   import PermissionDialog from './PermissionDialog';

   const CATEGORIES = ['general', 'productivity', 'development', 'ai', 'security', 'media'];

   interface StoreNodeProps {
     userId: string;
   }

   const StoreNode: React.FC<StoreNodeProps> = ({ userId }) => {
     const [searchQuery, setSearchQuery] = useState('');
     const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
     const [packages, setPackages] = useState<StorePackage[]>([]);
     const [total, setTotal] = useState(0);
     const [page, setPage] = useState(1);
     const [loading, setLoading] = useState(false);
     const [selectedPackage, setSelectedPackage] = useState<StorePackage | null>(null);
     const [showPermissionDialog, setShowPermissionDialog] = useState(false);
     const [installTarget, setInstallTarget] = useState<StorePackage | null>(null);
     const [error, setError] = useState<string | null>(null);

     const loadPackages = useCallback(async () => {
       setLoading(true);
       setError(null);
       try {
         const result: SearchResult = await searchPackages(
           searchQuery || undefined,
           selectedCategory,
           page,
         );
         setPackages(result.packages);
         setTotal(result.total);
       } catch (err) {
         setError(err instanceof Error ? err.message : 'Error cargando paquetes');
       } finally {
         setLoading(false);
       }
     }, [searchQuery, selectedCategory, page]);

     useEffect(() => {
       loadPackages();
     }, [loadPackages]);

     const handleSearch = (e: React.FormEvent) => {
       e.preventDefault();
       setPage(1);
       loadPackages();
     };

     const handleInstallClick = (pkg: StorePackage) => {
       setInstallTarget(pkg);
       setShowPermissionDialog(true);
     };

     const handleInstallConfirm = async () => {
       setShowPermissionDialog(false);
       if (installTarget) {
         // Instalar paquete (implementado en backend)
         setInstallTarget(null);
       }
     };

     return (
       <div className="store-node" data-testid="store-node">
         <header className="store-header">
           <h1>🏪 YEYO Store</h1>
           <form onSubmit={handleSearch} className="store-search">
             <input
               type="text"
               placeholder="Buscar paquetes..."
               value={searchQuery}
               onChange={(e) => setSearchQuery(e.target.value)}
               data-testid="store-search-input"
             />
             <button type="submit" data-testid="store-search-button">Buscar</button>
           </form>
         </header>

         <nav className="store-categories" data-testid="store-categories">
           <button
             className={!selectedCategory ? 'active' : ''}
             onClick={() => { setSelectedCategory(undefined); setPage(1); }}
           >
             Todos
           </button>
           {CATEGORIES.map((cat) => (
             <button
               key={cat}
               className={selectedCategory === cat ? 'active' : ''}
               onClick={() => { setSelectedCategory(cat); setPage(1); }}
             >
               {cat.charAt(0).toUpperCase() + cat.slice(1)}
             </button>
           ))}
         </nav>

         {error && <div className="store-error" data-testid="store-error">{error}</div>}

         {loading ? (
           <div className="store-loading" data-testid="store-loading">Cargando...</div>
         ) : selectedPackage ? (
           <PackageDetail
             pkg={selectedPackage}
             userId={userId}
             onBack={() => setSelectedPackage(null)}
             onInstall={() => handleInstallClick(selectedPackage)}
           />
         ) : (
           <div className="store-grid" data-testid="store-grid">
             {packages.map((pkg) => (
               <PackageCard
                 key={pkg.package_id}
                 pkg={pkg}
                 onClick={() => setSelectedPackage(pkg)}
                 onInstall={() => handleInstallClick(pkg)}
               />
             ))}
             {packages.length === 0 && (
               <p className="store-empty">No se encontraron paquetes</p>
             )}
           </div>
         )}

         {total > 20 && (
           <div className="store-pagination">
             <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
             <span>Página {page} de {Math.ceil(total / 20)}</span>
             <button disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(page + 1)}>Siguiente</button>
           </div>
         )}

         {showPermissionDialog && installTarget && (
           <PermissionDialog
             pkg={installTarget}
             onConfirm={handleInstallConfirm}
             onCancel={() => { setShowPermissionDialog(false); setInstallTarget(null); }}
           />
         )}
       </div>
     );
   };

   export default StoreNode;

4. Crear archivo frontend/src/components/store/PackageCard.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/store/PackageCard.tsx
   Contenido:

   import React from 'react';
   import { StorePackage } from '../../services/storeApi';

   interface PackageCardProps {
     pkg: StorePackage;
     onClick: () => void;
     onInstall: () => void;
   }

   const PackageCard: React.FC<PackageCardProps> = ({ pkg, onClick, onInstall }) => {
     const stars = '★'.repeat(Math.round(pkg.avg_rating)) +
                   '☆'.repeat(5 - Math.round(pkg.avg_rating));

     return (
       <div className="package-card" data-testid="package-card" onClick={onClick}>
         <h3>{pkg.manifest.name}</h3>
         <p className="package-version">v{pkg.manifest.version}</p>
         <p className="package-description">{pkg.manifest.description}</p>
         <div className="package-meta">
           <span className="package-rating" title={`${pkg.avg_rating}/5`}>{stars}</span>
           <span className="package-downloads">{pkg.download_count} descargas</span>
         </div>
         <div className="package-tags">
           {pkg.manifest.tags.map((tag) => (
             <span key={tag} className="package-tag">{tag}</span>
           ))}
         </div>
         <button
           className="package-install-btn"
           data-testid="install-button"
           onClick={(e) => { e.stopPropagation(); onInstall(); }}
         >
           Instalar
         </button>
       </div>
     );
   };

   export default PackageCard;

5. Crear archivo frontend/src/components/store/PackageDetail.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/store/PackageDetail.tsx
   Contenido:

   import React, { useState, useEffect } from 'react';
   import { StorePackage, PackageReview, getReviews, submitReview } from '../../services/storeApi';

   interface PackageDetailProps {
     pkg: StorePackage;
     userId: string;
     onBack: () => void;
     onInstall: () => void;
   }

   const PackageDetail: React.FC<PackageDetailProps> = ({ pkg, userId, onBack, onInstall }) => {
     const [reviews, setReviews] = useState<PackageReview[]>([]);
     const [newRating, setNewRating] = useState(5);
     const [newComment, setNewComment] = useState('');

     useEffect(() => {
       getReviews(pkg.package_id).then(setReviews).catch(() => {});
     }, [pkg.package_id]);

     const handleSubmitReview = async (e: React.FormEvent) => {
       e.preventDefault();
       try {
         const review = await submitReview(pkg.package_id, newRating, newComment, userId);
         setReviews([...reviews, review]);
         setNewComment('');
       } catch {
         // Error handled by UI
       }
     };

     return (
       <div className="package-detail" data-testid="package-detail">
         <button onClick={onBack} data-testid="back-button">← Volver</button>
         <h2>{pkg.manifest.name} <span>v{pkg.manifest.version}</span></h2>
         <p>{pkg.manifest.description}</p>
         <p><strong>Autor:</strong> {pkg.manifest.author}</p>
         <p><strong>Licencia:</strong> {pkg.manifest.license}</p>
         <p><strong>Categoría:</strong> {pkg.manifest.category}</p>

         <div className="package-permissions">
           <h3>Permisos requeridos:</h3>
           <ul>
             {pkg.manifest.permissions.map((perm) => (
               <li key={perm}>{perm}</li>
             ))}
             {pkg.manifest.permissions.length === 0 && <li>Ninguno</li>}
           </ul>
         </div>

         <button className="install-btn" onClick={onInstall} data-testid="detail-install-button">
           Instalar paquete
         </button>

         <div className="package-reviews" data-testid="reviews-section">
           <h3>Reviews ({reviews.length})</h3>
           {reviews.map((r) => (
             <div key={r.review_id} className="review">
               <span>{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
               <p>{r.comment}</p>
             </div>
           ))}

           <form onSubmit={handleSubmitReview} className="review-form">
             <h4>Dejar review</h4>
             <select value={newRating} onChange={(e) => setNewRating(Number(e.target.value))}>
               {[5, 4, 3, 2, 1].map((n) => (
                 <option key={n} value={n}>{n} {'★'.repeat(n)}</option>
               ))}
             </select>
             <textarea
               value={newComment}
               onChange={(e) => setNewComment(e.target.value)}
               placeholder="Escribe tu review..."
               data-testid="review-comment"
             />
             <button type="submit" data-testid="submit-review">Enviar review</button>
           </form>
         </div>
       </div>
     );
   };

   export default PackageDetail;

6. Crear archivo frontend/src/components/store/PermissionDialog.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/store/PermissionDialog.tsx
   Contenido:

   import React from 'react';
   import { StorePackage } from '../../services/storeApi';

   interface PermissionDialogProps {
     pkg: StorePackage;
     onConfirm: () => void;
     onCancel: () => void;
   }

   const PERMISSION_DESCRIPTIONS: Record<string, string> = {
     'filesystem.read': '📁 Leer archivos del sistema',
     'filesystem.write': '📝 Escribir archivos en el sistema',
     'network.local': '🔌 Acceso a red local',
     'network.internet': '🌐 Acceso a internet',
     'gpu.access': '🎮 Usar GPU para procesamiento',
     'system.info': 'ℹ️ Leer información del sistema',
     'notifications': '🔔 Enviar notificaciones',
   };

   const PermissionDialog: React.FC<PermissionDialogProps> = ({ pkg, onConfirm, onCancel }) => {
     const permissions = pkg.manifest.permissions;

     return (
       <div className="permission-dialog-overlay" data-testid="permission-dialog">
         <div className="permission-dialog">
           <h2>⚠️ Permisos requeridos</h2>
           <p>
             <strong>{pkg.manifest.name}</strong> v{pkg.manifest.version} solicita los siguientes permisos:
           </p>

           {permissions.length > 0 ? (
             <ul className="permission-list">
               {permissions.map((perm) => (
                 <li key={perm}>
                   {PERMISSION_DESCRIPTIONS[perm] || perm}
                 </li>
               ))}
             </ul>
           ) : (
             <p className="no-permissions">✅ Este paquete no requiere permisos especiales</p>
           )}

           <div className="permission-actions">
             <button onClick={onCancel} data-testid="permission-cancel">Cancelar</button>
             <button onClick={onConfirm} className="confirm-btn" data-testid="permission-confirm">
               Instalar
             </button>
           </div>
         </div>
       </div>
     );
   };

   export default PermissionDialog;

7. Crear archivo frontend/src/__tests__/store/StoreNode.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/store/StoreNode.test.tsx
   Contenido:

   /**
    * Tests para YEYO Store Frontend — Micro-fase 7.5
    */

   import React from 'react';
   import { render, screen, fireEvent, waitFor } from '@testing-library/react';
   import StoreNode from '../../components/store/StoreNode';
   import * as storeApi from '../../services/storeApi';

   jest.mock('../../services/storeApi');
   const mockedApi = storeApi as jest.Mocked<typeof storeApi>;

   const mockPackage: storeApi.StorePackage = {
     package_id: 'pkg-1',
     manifest: {
       name: 'test-pkg',
       version: '1.0.0',
       description: 'A test package',
       author: 'Test Dev',
       permissions: ['filesystem.read'],
       category: 'general',
       tags: ['test'],
       license: 'MIT',
     },
     developer_id: 'dev-1',
     status: 'published',
     security_score: 95,
     download_count: 100,
     avg_rating: 4.5,
     total_reviews: 10,
     published_at: '2025-01-01',
   };

   describe('StoreNode', () => {
     beforeEach(() => {
       mockedApi.searchPackages.mockResolvedValue({
         packages: [mockPackage],
         total: 1,
         page: 1,
         per_page: 20,
       });
     });

     it('renders store node', async () => {
       render(<StoreNode userId="user-1" />);
       await waitFor(() => {
         expect(screen.getByTestId('store-node')).toBeInTheDocument();
       });
     });

     it('displays search input', async () => {
       render(<StoreNode userId="user-1" />);
       await waitFor(() => {
         expect(screen.getByTestId('store-search-input')).toBeInTheDocument();
       });
     });

     it('shows categories', async () => {
       render(<StoreNode userId="user-1" />);
       await waitFor(() => {
         expect(screen.getByTestId('store-categories')).toBeInTheDocument();
       });
     });

     it('displays packages after load', async () => {
       render(<StoreNode userId="user-1" />);
       await waitFor(() => {
         expect(screen.getByTestId('store-grid')).toBeInTheDocument();
       });
     });

     it('shows permission dialog on install', async () => {
       render(<StoreNode userId="user-1" />);
       await waitFor(() => {
         const installBtn = screen.getByTestId('install-button');
         fireEvent.click(installBtn);
       });
       expect(screen.getByTestId('permission-dialog')).toBeInTheDocument();
     });

     it('calls searchPackages on search', async () => {
       render(<StoreNode userId="user-1" />);
       await waitFor(() => {
         const input = screen.getByTestId('store-search-input');
         fireEvent.change(input, { target: { value: 'neural' } });
         fireEvent.click(screen.getByTestId('store-search-button'));
       });
       expect(mockedApi.searchPackages).toHaveBeenCalled();
     });
   });

8. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npm test -- --watchAll=false --testPathPattern=store

VERIFICAR:
- [ ] frontend/src/components/store/ tiene StoreNode, PackageCard, PackageDetail, PermissionDialog
- [ ] frontend/src/services/storeApi.ts tiene API client completo
- [ ] StoreNode renderiza con búsqueda, categorías, grid de paquetes
- [ ] Install button muestra PermissionDialog con lista de permisos
- [ ] PackageDetail muestra reviews y permite dejar review
- [ ] TODOS los tests pasan

SI FALLA:
- React/TypeScript: npm install (en frontend/)
- @testing-library/react: npm install @testing-library/react @testing-library/jest-dom

NO HACER:
- No implementar backend de instalación real
- No conectar a Store API real en tests

GATE: Store UI renderiza, búsqueda funciona, diálogo de permisos muestra al instalar, reviews funcionan, todos los tests pasan.
```
