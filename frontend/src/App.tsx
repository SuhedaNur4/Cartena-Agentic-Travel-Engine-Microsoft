import { Link, Outlet, useLocation } from 'react-router-dom'

function Navbar() {
  const location = useLocation()

  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '20px 40px',
        background: '#12241d', 
        color: '#F5ECD2',      
        borderBottom: '1px solid rgba(255,255,255,.08)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <img 
          src="/cartenalogo.png" 
          alt="Cartena Logo"
          style={{ width: '32px', height: '32px', borderRadius: '50%', objectFit: 'cover' }} 
        />
        <Link to="/" style={{ color: '#F5ECD2', textDecoration: 'none', fontWeight: 700, fontSize: '18px', letterSpacing: '-0.02em' }}>
          Cartena
        </Link>
      </div>

      <div style={{ display: 'flex', gap: '30px', fontWeight: 500, fontSize: '14px', color: 'rgba(245,236,210,.72)' }}>
        <Link to="/" style={{ color: location.pathname === '/' ? '#FBB728' : 'inherit', textDecoration: 'none' }}>Planner</Link>
        <Link to="/history" style={{ color: location.pathname === '/history' ? '#FBB728' : 'inherit', textDecoration: 'none' }}>History</Link>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
      </div>
    </nav>
  )
}

export function App() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Outlet />
      </div>

      <div style={{ padding: '22px 40px', background: '#0d1f18', color: 'rgba(245,236,210,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 500, fontSize: '12px' }}>
        <span>Cartena</span>
      </div>
    </div>
  )
}

