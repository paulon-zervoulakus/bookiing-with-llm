import React, { useState, useEffect, useRef } from "react";
import { User, Booking, Message } from "../types";

interface BookingAppProps {
	user: User;
	onLogout: () => void;
}

const BookingApp: React.FC<BookingAppProps> = ({ user, onLogout }) => {
	const [isBotTyping, setIsBotTyping] = useState(false);
	const [bookings, setBookings] = useState<Booking[]>([]);
	const [formData, setFormData] = useState({
		name: user?.name || "",
		email: user?.email || "",
		schedule_date: "",
		schedule_time: "",
	});
	const [messages, setMessages] = useState<Message[]>([
		{
			type: "ai",
			text: `Hello ${user?.name}! I'm your booking assistant. How can I help you today?`,
		},
	]);
	const [streamingMessage, setStreamingMessage] = useState("");

	const [chatInput, setChatInput] = useState("");
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState("");
	const [success, setSuccess] = useState("");
	const [bookingStatus, setBookingStatus] = useState("");
	const abortControllerRef = useRef<AbortController | null>(null);

	useEffect(() => {
		fetchBookings();
	}, []);

	const fetchBookings = async () => {
		try {
			const response = await fetch("http://localhost:8000/api/appointments", {
				method: "GET",
				headers: {
					Authorization: `Bearer ${localStorage.getItem("booking_token")}`,
				},
			});
			const data = await response.json();
			setBookings(data);
		} catch (err) {
			setError("Failed to fetch bookings");
		}
	};

	const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setFormData({
			...formData,
			[e.target.name]: e.target.value,
		});
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsSubmitting(true);
		setError("");
		setSuccess("");

		try {
			const response = await fetch("http://localhost:8000/api/appointments", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${localStorage.getItem("booking_token")}`,
				},
				body: JSON.stringify(formData),
			});
			const newBooking = await response.json();

			setBookings([newBooking, ...bookings]);
			setFormData({
				name: user?.name || "",
				email: user?.email || "",
				schedule_date: "",
				schedule_time: "",
			});
			setSuccess("Booking created successfully!");

			setMessages((prev) => [
				...prev,
				{
					type: "ai",
					text: `Great! You've created booking for ${formData.name} on ${formData.schedule_date} at ${formData.schedule_time}.`,
				},
			]);
		} catch (err) {
			setError("Failed to create booking");
		}

		setIsSubmitting(false);
	};

	const handleDelete = async (bookingId: string) => {
		try {
			const response = await fetch(
				`http://localhost:8000/api/appointments/${bookingId}`,
				{
					method: "DELETE",
					headers: {
						Authorization: `Bearer ${localStorage.getItem("booking_token")}`,
					},
				}
			);
			const is_deleted = await response.json();
			if (is_deleted.status == "success") {
				setBookings(bookings.filter((b) => b.id !== bookingId));
				setSuccess(is_deleted.message);
			}
		} catch (err) {
			setError("Failed to delete booking");
		}
	};

	// Updated streaming chat handler
	const handleChatSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!chatInput.trim()) return;

		const userMessage = chatInput;
		setMessages((prev) => [...prev, { type: "human", text: userMessage }]);
		setChatInput("");
		setIsBotTyping(true);
		setBookingStatus("");

		// Cancel any ongoing request
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
		}

		abortControllerRef.current = new AbortController();

		try {
			const response = await fetch("http://localhost:8000/api/bot/ai-stream", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${localStorage.getItem("booking_token")}`,
				},
				body: JSON.stringify({ query: userMessage }),
				signal: abortControllerRef.current.signal,
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const reader = response.body?.getReader();
			if (!reader) {
				throw new Error("Response body is not readable");
			}

			const decoder = new TextDecoder();
			let buffer = "";
			// let currentAiMessage = "";

			while (true) {
				const { done, value } = await reader.read();

				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split("\n");
				buffer = lines.pop() || "";

				for (const line of lines) {
					if (line.startsWith("data: ")) {
						const jsonData = line.slice(6); // Remove 'data: ' prefix
						try {
							const data = JSON.parse(jsonData);
							console.log(data);
							if (data.type === "update") {
								handleStreamUpdate(data.data.short_message);
							} else if (data.type === "final") {
								handleStreamFinal(data);
							}
						} catch (error) {
							console.error("Error parsing JSON:", error);
						}
					}
				}
			}

			setIsBotTyping(false);
		} catch (err) {
			if ((err as Error).name !== "AbortError") {
				console.error("Streaming error:", err);
				setMessages((prev) => [
					...prev,
					{
						type: "ai",
						text: "Sorry, I encountered an error. Please try again.",
					},
				]);
			}
			setIsBotTyping(false);
		}
	};
	const handleStreamUpdate = (short_message: string) => {
		setStreamingMessage("Processing : " + short_message);
	};
	const handleStreamFinal = (data: any) => {
		if (data.ai_response && data.ai_response.length > 0) {
			const lastResponse = data.ai_response[data.ai_response.length - 1];
			if (lastResponse.type === "AIMessage") {
				setMessages((prev) => [
					...prev,
					{
						type: "ai",
						text: lastResponse.content,
					},
				]);
			}
		}

		// Handle booking status
		const booking_status = data.booking_status;
		if (booking_status) {
			if (booking_status.toUpperCase() === "CONFIRMED") {
				fetchBookings();
			}
			setBookingStatus(booking_status);
		}
	};
	const handleTestStream = (data: string, response_type: string) => {
		if (response_type == "buffering") {
			setMessages((prev) => {
				const newMessages = [...prev];
				const lastMessage = newMessages[newMessages.length - 1];
				if (
					lastMessage &&
					lastMessage.type === "buffering" &&
					lastMessage.text.includes("...processing")
				) {
					lastMessage.text = `🤖 Processing: ${data}...`;
				} else {
					newMessages.push({
						type: "buffering",
						text: `🤖 Processing: ${data}...`,
					});
				}
				return newMessages;
			});
		} else if (response_type == "final") {
			setMessages((prev) => [
				...prev,
				{
					type: "ai",
					text: data,
				},
			]);
		}
	};

	const handleStreamData = (data: any) => {
		console.log("data", data);
		if (data.type === "update") {
			// Handle intermediate updates - you can show progress here
			console.log("Node update:", data.node);
			// Optional: Show which node is currently processing
			// setMessages(prev => {
			//   const newMessages = [...prev];
			//   const lastMessage = newMessages[newMessages.length - 1];
			//   if (lastMessage && lastMessage.type === 'ai' && lastMessage.text.includes('...processing')) {
			//     lastMessage.text = `🤖 Processing: ${Object.keys(data.data)[0]}...`;
			//   } else {
			//     newMessages.push({
			//       type: 'ai',
			//       text: `🤖 Processing: ${Object.keys(data.data)[0]}...`
			//     });
			//   }
			//   return newMessages;
			// });
		} else if (data.type === "final") {
			// Handle final response
			if (data.ai_response && data.ai_response.length > 0) {
				const lastResponse = data.ai_response[data.ai_response.length - 1];
				if (lastResponse.type === "AIMessage") {
					setMessages((prev) => [
						...prev,
						{
							type: "ai",
							text: lastResponse.content,
						},
					]);
				}
			}

			// Handle booking status
			const booking_status = data.booking_status;
			setBookingStatus(booking_status);

			if (booking_status && booking_status.toUpperCase() === "CONFIRMED") {
				fetchBookings();
			}
		} else if (data.type === "token") {
			// Handle token streaming for real-time typing effect
			setMessages((prev) => {
				const newMessages = [...prev];
				const lastMessage = newMessages[newMessages.length - 1];

				if (
					lastMessage &&
					lastMessage.type === "ai" &&
					lastMessage.text.includes("...thinking...")
				) {
					// Replace thinking message with actual content
					lastMessage.text = data.content;
				} else if (
					lastMessage &&
					lastMessage.type === "ai" &&
					!lastMessage.text.includes("...thinking...")
				) {
					// Append to existing AI message
					lastMessage.text += data.content;
				} else {
					// Create new AI message
					newMessages.push({
						type: "ai",
						text: data.content,
					});
				}

				return newMessages;
			});
		}
	};

	const cancelStream = () => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort();
		}
		setIsBotTyping(false);
	};

	// Cleanup on unmount
	useEffect(() => {
		return () => {
			if (abortControllerRef.current) {
				abortControllerRef.current.abort();
			}
		};
	}, []);

	return (
		<div className="app">
			<header className="header">
				<h1>📅 Booking Platform with Agentic (AI) Assistance</h1>
				<div className="human-info">
					<img
						src={user?.picture || "https://via.placeholder.com/40"}
						alt="User"
						className="human-avatar"
					/>
					<span>{user?.name}</span>
					<button className="logout-btn" onClick={onLogout}>
						Logout
					</button>
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
										min={new Date().toISOString().split("T")[0]}
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

							<button
								type="submit"
								className="submit-btn"
								disabled={isSubmitting}
							>
								{isSubmitting ? "Creating..." : "Create Booking"}
							</button>
						</form>
					</div>

					{/* Booking List */}
					<div className="booking-list">
						<h3>Appointment Bookings ({bookings.length})</h3>

						{bookings.length === 0 ? (
							<div className="empty-state">
								No bookings yet. Create your first booking above!
							</div>
						) : (
							bookings.map((booking) => (
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
										📧 {booking.email}
										<br />
										📅 {booking.schedule_date} at {booking.schedule_time}
										<br />
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
							🤖 Agentic Assistant
							{bookingStatus && (
								<span className="booking-status">Status: {bookingStatus}</span>
							)}
						</div>

						<div className="chat-messages">
							{messages.map((message, index) => (
								<div key={index} className={`message ${message.type}`}>
									<pre
										style={{
											margin: 0,
											whiteSpace: "pre-wrap",
											wordBreak: "break-word",
										}}
									>
										{message.text}
									</pre>
								</div>
							))}
							{isBotTyping && (
								<div className="message ai">
									<pre style={{ margin: 0 }}>
										<span
											className="spinner"
											style={{ marginRight: "8px" }}
										></span>
										{streamingMessage}
										<button
											onClick={cancelStream}
											style={{
												marginLeft: "10px",
												fontSize: "12px",
												padding: "2px 6px",
												background: "#ff4444",
												color: "white",
												border: "none",
												borderRadius: "3px",
												cursor: "pointer",
											}}
										>
											Cancel
										</button>
									</pre>
								</div>
							)}
						</div>

						<form onSubmit={handleChatSubmit} className="chat-input-container">
							<input
								type="text"
								className="chat-input"
								value={chatInput}
								onChange={(e) => setChatInput(e.target.value)}
								placeholder="Ask me anything about bookings..."
								disabled={isBotTyping}
							/>
							<button
								type="submit"
								className="chat-send-btn"
								disabled={isBotTyping}
							>
								{isBotTyping ? "Sending..." : "Send"}
							</button>
						</form>
					</div>
				</div>
			</div>
		</div>
	);
};

export default BookingApp;
