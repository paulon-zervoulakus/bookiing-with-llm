import { useState, useEffect } from 'react';
import AuthPage from './components/AuthPage';
import BookingApp from './components/BookingApp';
import { AuthData } from './types';
import { initializeGoogleAuth } from './services/googleAuth';

function App() {
  const [authData, setAuthData] = useState<AuthData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initApp = async () => {
      try {
        // Initialize Google Auth
        await initializeGoogleAuth();
        
        // Check for existing auth token
        const token = localStorage.getItem('booking_token');
        const userData = localStorage.getItem('booking_user');
        
        if (token && userData) {
          setAuthData({
            access_token: token,
            user: JSON.parse(userData)
          });
        }
      } catch (error) {
        console.error('Failed to initialize app:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initApp();
  }, []);

  const handleLogin = (data: AuthData) => {
    setAuthData(data);
    localStorage.setItem('booking_token', data.access_token);
    localStorage.setItem('booking_user', JSON.stringify(data.user));
  };

  const handleLogout = () => {
    setAuthData(null);
    localStorage.removeItem('booking_token');
    localStorage.removeItem('booking_user');
    
    // Sign out from Google
    // if (window.google) {
    //   window.google.accounts.id.disableAutoSelect();
    // }
  };

  if (isLoading) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Loading...</h1>
        </div>
      </div>
    );
  }
  

  return (
    <div className="app">
      {!authData ? (
        <AuthPage onLogin={handleLogin} />
      ) : (
        <BookingApp user={authData.user} onLogout={handleLogout} />
      )}
    </div>
  );
}

export default App;