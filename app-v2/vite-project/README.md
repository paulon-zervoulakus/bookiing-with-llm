# Booking Platform

A modern React.js booking platform with Google OAuth authentication and real-time chat functionality.

## Features

- 🔐 Google OAuth Authentication
- 📅 Booking Management (Create, View, Delete)
- 🤖 AI Chat Assistant
- 📱 Responsive Design
- ⚡ Built with Vite + React + TypeScript

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Google OAuth Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to "Credentials" and create an OAuth 2.0 Client ID
5. Configure the authorized origins:
   - For development: `http://localhost:3000`
   - For production: your domain
6. Copy the Client ID

### 3. Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your Google Client ID:
   ```
   VITE_GOOGLE_CLIENT_ID=your-actual-google-client-id.apps.googleusercontent.com
   VITE_API_BASE_URL=http://localhost:8000
   ```

### 4. Run the Application

```bash
# Development mode
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The application will be available at `http://localhost:3000`

## Google OAuth Integration

This project uses the new Google Identity Services (GIS) library for authentication. The integration includes:

- **Client-side authentication** using the Google Sign-In button
- **JWT token decoding** to extract user information
- **Secure token storage** in localStorage
- **Automatic sign-out** functionality

### Security Notes

⚠️ **Important for Production:**

1. **Token Verification**: The current implementation decodes JWT tokens on the client-side for demo purposes. In production, always verify Google tokens on your backend server.

2. **Backend Integration**: You should send the Google credential to your backend API for verification:
   ```typescript
   const response = await fetch('/api/auth/google', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ credential: googleCredential })
   });
   ```

3. **Token Storage**: Consider using secure HTTP-only cookies instead of localStorage for production applications.

## Project Structure

```
src/
├── components/           # React components
│   ├── AuthPage.tsx     # Google OAuth login page
│   └── BookingApp.tsx   # Main booking application
├── services/            # Service layer
│   └── googleAuth.ts    # Google authentication utilities
├── types/               # TypeScript type definitions
│   └── index.ts         # All type definitions
├── App.tsx              # Main app component
├── main.tsx             # Application entry point
└── index.css            # Global styles
```

## API Integration

The current implementation uses mock data for demonstration. To integrate with a real backend:

1. Update the API endpoints in the components
2. Add proper error handling
3. Implement authentication headers
4. Add loading states

Example API integration:

```typescript
// Replace mock data with real API calls
const response = await fetch('/api/bookings', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('booking_token')}`
  }
});
const bookings = await response.json();
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Technologies Used

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Google Identity Services** - OAuth authentication
- **CSS3** - Styling with modern features

## Browser Support

This application uses modern web APIs and requires:
- Chrome/Edge 88+
- Firefox 78+
- Safari 14+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details