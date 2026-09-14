import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Gamepad2, 
  Search, 
  DownloadCloud, 
  ListOrdered, 
  Settings, 
  PlusCircle,
  History,
  Info
} from 'lucide-react';

const Sidebar = () => {
  const navItems = [
    { to: '/', icon: <Gamepad2 size={20} />, label: 'Library' },
    { to: '/add', icon: <PlusCircle size={20} />, label: 'Add New' },
    { to: '/wanted', icon: <Search size={20} />, label: 'Wanted' },
    { to: '/activity', icon: <History size={20} />, label: 'Activity' },
    { to: '/settings', icon: <Settings size={20} />, label: 'Settings' },
  ];

  return (
    <aside className="sidebar">
      <div style={{ padding: '20px', borderBottom: '1px solid var(--border-color)', marginBottom: '10px' }}>
        <h2 style={{ fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--primary-color)' }}>
          <Gamepad2 size={24} /> Romarr
        </h2>
      </div>
      <nav style={{ padding: '0 10px' }}>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 16px',
              borderRadius: '6px',
              marginBottom: '4px',
              color: isActive ? 'var(--highlight-color)' : 'var(--text-primary)',
              backgroundColor: isActive ? 'var(--sidebar-active)' : 'transparent',
              textDecoration: 'none',
              transition: 'all 0.2s',
              fontSize: '0.95rem'
            })}
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div style={{ marginTop: 'auto', padding: '20px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        Romarr v0.1.0
      </div>
    </aside>
  );
};

export default Sidebar;
