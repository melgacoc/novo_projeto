import { type RouteConfig, index, route } from '@react-router/dev/routes'

export default [
  index('routes/index.tsx'),
  route('sitemap.xml', 'routes/sitemap.ts'),
  route('robots.txt', 'routes/robots.ts'),
  route('auth/callback', 'routes/auth-callback.tsx'),

  // painel da operadora: só no navegador (sem SSR)
  route('painel', 'routes/painel/layout.tsx', [
    index('routes/painel/dashboard.tsx'),
    route('passeios', 'routes/painel/tours.tsx'),
    route('passeios/novo', 'routes/painel/tour-new.tsx'),
    route('passeios/:id', 'routes/painel/tour-edit.tsx'),
    route('agenda', 'routes/painel/agenda.tsx'),
    route('reservas', 'routes/painel/bookings.tsx'),
    route('extrato', 'routes/painel/statement.tsx'),
    route('perfil', 'routes/painel/profile.tsx'),
    route('convite', 'routes/painel/invite.tsx'),
  ]),

  // admin: só no navegador (sem SSR)
  route('admin', 'routes/admin/layout.tsx', [
    index('routes/admin/dashboard.tsx'),
    route('operadoras', 'routes/admin/operators.tsx'),
    route('operadoras/:id', 'routes/admin/operator-detail.tsx'),
    route('passeios', 'routes/admin/tours.tsx'),
    route('passeios/:id', 'routes/admin/tour-review.tsx'),
    route('passeios/:id/editar', 'routes/admin/tour-edit.tsx'),
    route('reservas', 'routes/admin/bookings.tsx'),
    route('repasses', 'routes/admin/payouts.tsx'),
    route('categorias', 'routes/admin/categories.tsx'),
    route('usuarios', 'routes/admin/users.tsx'),
    route('configuracoes', 'routes/admin/settings.tsx'),
    route('auditoria', 'routes/admin/audit.tsx'),
  ]),

  // site do turista: renderizado no servidor (SEO), navegação fluida depois da primeira carga
  route(':lang', 'routes/public/layout.tsx', [
    index('routes/public/home.tsx'),
    route('passeios', 'routes/public/search.tsx'),
    route('passeios/:slug', 'routes/public/tour.tsx'),
    route('checkout/:code', 'routes/public/checkout.tsx'),
    route('reservas', 'routes/public/my-bookings.tsx'),
    route('reservas/:code', 'routes/public/booking.tsx'),
    route('entrar', 'routes/public/login.tsx'),
    route('termos', 'routes/public/terms.tsx'),
    route('privacidade', 'routes/public/privacy.tsx'),
    route('*', 'routes/public/not-found.tsx'),
  ]),
] satisfies RouteConfig
