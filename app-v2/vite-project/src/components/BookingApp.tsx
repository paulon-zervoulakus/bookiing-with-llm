import React, { useState, useEffect } from 'react';
import { User, Booking, Message } from '../types';

interface BookingAppProps {
  user: User;
  onLogout: () => void;
}

const BookingApp: React.FC<BookingAppProps> = ({ user, onLogout }) => {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    schedule_date: '',
    schedule_time: ''
  });
  const [messages, setMessages] = useState<Message[]>([
    { type: 'bot', text: `Hello ${user?.name}! I'm your booking assistant. How can I help you today?` }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    try {
      // Replace with your actual API endpoint
      const response = await fetch('http://localhost:8000/api/appointments', {
        method: "GET",
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('booking_token')}`
        }
      });
      const data = await response.json();
      setBookings(data);

      // // Mock data for now
      // const mockBookings: Booking[] = [
      //   {
      //     id: 1,
      //     name: 'John Doe',
      //     email: 'john@example.com',
      //     schedule_date: '2025-07-15',
      //     schedule_time: '10:00',
      //     created_at: new Date().toISOString()
      //   },
      //   {
      //     id: 2,
      //     name: 'Jane Smith',
      //     email: 'jane@example.com',
      //     schedule_date: '2025-07-16',
      //     schedule_time: '14:30',
      //     created_at: new Date().toISOString()
      //   }
      // ];
      // setBookings(mockBookings);
    } catch (err) {
      setError('Failed to fetch bookings');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    setSuccess('');

    try {
      // Replace with your actual API endpoint
      const response = await fetch('http://localhost:8000/api/appointments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('booking_token')}`
        },
        body: JSON.stringify(formData)
      });
      const newBooking = await response.json();

      // // Mock API call for now
      // const newBooking: Booking = {
      //   id: Date.now(),
      //   ...formData,
      //   created_at: new Date().toISOString()
      // };
      
      setBookings([newBooking, ...bookings]);
      setFormData({
        name: user?.name || '',
        email: user?.email || '',
        schedule_date: '',
        schedule_time: ''
      });
      setSuccess('Booking created successfully!');
      
      // Add success message to chat
      setMessages(prev => [...prev, 
        { type: 'bot', text: `Great! I've created your booking for ${formData.name} on ${formData.schedule_date} at ${formData.schedule_time}.` }
      ]);
    } catch (err) {
      setError('Failed to create booking');
    }

    setIsSubmitting(false);
  };

  const handleDelete = async (bookingId: string) => {
    try {
      // Replace with your actual API endpoint
      const response = await fetch(`http://localhost:8000/api/appointments/${bookingId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('booking_token')}`
        }
      });
      const is_deleted = await response.json()
      if(is_deleted.status == "success"){
        setBookings(bookings.filter(b => b.id !== bookingId));
        setSuccess(is_deleted.message);
      }

    } catch (err) {
      setError('Failed to delete booking');
    }
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMessage = chatInput;
    setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    setChatInput('');

    try {
      // Replace with your actual chatbot API
      const response = await fetch('http://localhost:8000/api/bot/agentic', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('booking_token')}`
        },
        body: JSON.stringify({ query: userMessage })
      });
      const data = await response.json();

      // Mock chat response for now
      // let botResponse = "I'm here to help with your bookings!";
      
      // if (userMessage.toLowerCase().includes('create') || userMessage.toLowerCase().includes('book')) {
      //   botResponse = "To create a new booking, please fill out the form on the left with the required details: name, email, date, and time.";
      // } else if (userMessage.toLowerCase().includes('list') || userMessage.toLowerCase().includes('show')) {
      //   botResponse = `You currently have ${bookings.length} booking(s). You can see them all in the booking list above.`;
      // } else if (userMessage.toLowerCase().includes('help')) {
      //   botResponse = "I can help you create bookings, view your existing bookings, or answer questions about the platform. What would you like to do?";
      // } else if (userMessage.toLowerCase().includes('delete') || userMessage.toLowerCase().includes('cancel')) {
      //   botResponse = "To delete a booking, click the red 'Delete' button next to any booking in your list above.";
      // }
      console.log(data["ai_response"][0]["content"])
      setTimeout(() => {
        setMessages(prev => [...prev, { type: 'bot', text: data["ai_response"][data["ai_response"].length -1]["content"] }]);
      }, 500);
    } catch (err) {
      setMessages(prev => [...prev, { type: 'bot', text: 'Sorry, I encountered an error. Please try again.' }]);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>📅 Booking Platform</h1>
        <div className="user-info">
          <img src={user?.picture || 'https://via.placeholder.com/40'} alt="User" className="user-avatar" />
          <span>{user?.name}</span>
          <button className="logout-btn" onClick={onLogout}>Logout</button>
        </div>
      </header>

      <div className="main-content">
        <div className="left-column">
          {/* Booking Form */}
          <div className="booking-form">
            <h3>Create New Booking</h3>
            
            {error && <div className="error-message">{error}</div>}
            {success && <div className="success-message">{success}</div>}
            
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter full name"
                />
              </div>
              
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter email address"
                />
              </div>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Date</label>
                  <input
                    type="date"
                    name="schedule_date"
                    value={formData.schedule_date}
                    onChange={handleInputChange}
                    required
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>
                
                <div className="form-group">
                  <label>Time</label>
                  <input
                    type="time"
                    name="schedule_time"
                    value={formData.schedule_time}
                    onChange={handleInputChange}
                    required
                  />
                </div>
              </div>
              
              <button type="submit" className="submit-btn" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create Booking'}
              </button>
            </form>
          </div>

          {/* Booking List */}
          <div className="booking-list">
            <h3>Your Bookings ({bookings.length})</h3>
            
            {bookings.length === 0 ? (
              <div className="empty-state">
                No bookings yet. Create your first booking above!
              </div>
            ) : (
              bookings.map(booking => (
                <div key={booking.id} className="booking-item">
                  <div className="booking-header">
                    <div className="booking-name">{booking.name}</div>
                    <button
                      className="delete-btn"
                      onClick={() => handleDelete(booking.id)}
                    >
                      Delete
                    </button>
                  </div>
                  <div className="booking-details">
                    📧 {booking.email}<br/>
                    📅 {booking.schedule_date} at {booking.schedule_time}<br/>
                    🕒 Created: {new Date(booking.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="right-column">
          {/* Chat Interface */}
          <div className="chat-container">
            <div className="chat-header">
              🤖 Booking Assistant
            </div>
            
            <div className="chat-messages">
              {messages.map((message, index) => (
                <div key={index} className={`message ${message.type}`}>
                  {message.text}
                </div>
              ))}
            </div>
            
            <form onSubmit={handleChatSubmit} className="chat-input-container">
              <input
                type="text"
                className="chat-input"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask me anything about bookings..."
              />
              <button type="submit" className="chat-send-btn">
                Send
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BookingApp;