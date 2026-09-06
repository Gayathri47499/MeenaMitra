import { useState } from "react";
import {
  Send,
  Fish,
  LogOut,
  Plus,
  MessageCircle,
  Menu,
  X,
  Sparkles,
} from "lucide-react";

import "./App.css";


const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";


function App() {

  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const [showSignup, setShowSignup] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [question, setQuestion] = useState("");

  const [messages, setMessages] = useState([]);

  const [history, setHistory] = useState([]);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const [sidebarOpen, setSidebarOpen] = useState(true);


  // ==========================================================
  // SIGNUP
  // ==========================================================

  async function handleSignup(e) {

    e.preventDefault();

    setError("");

    try {

      const response = await fetch(`${API_URL}/signup`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          email,
          password,
        }),
      });


      const data = await response.json();


      if (!response.ok) {
        throw new Error(data.detail || "Signup failed");
      }


      if (data.access_token) {

        localStorage.setItem(
          "meenamitra_token",
          data.access_token
        );

        setIsLoggedIn(true);

      } else {

        setError(
          "Signup successful. Please check your email to confirm your account, then login."
        );

        setShowSignup(false);
      }

    } catch (err) {

      setError(err.message);

    }
  }


  // ==========================================================
  // LOGIN
  // ==========================================================

  async function handleLogin(e) {

    e.preventDefault();

    setError("");

    try {

      const response = await fetch(`${API_URL}/login`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          email,
          password,
        }),
      });


      const data = await response.json();


      if (!response.ok) {
        throw new Error(data.detail || "Login failed");
      }


      localStorage.setItem(
        "meenamitra_token",
        data.access_token
      );


      setIsLoggedIn(true);

      loadHistory(data.access_token);


    } catch (err) {

      setError(err.message);

    }
  }


  // ==========================================================
  // LOAD CHAT HISTORY
  // ==========================================================

  async function loadHistory(token) {

    try {

      const response = await fetch(
        `${API_URL}/history`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );


      const data = await response.json();


      if (response.ok) {

        setHistory(
          data.conversations || []
        );

      }

    } catch (err) {

      console.error(err);

    }
  }


  // ==========================================================
  // SEND CHAT
  // ==========================================================

  async function sendMessage(e) {

    e.preventDefault();

    if (!question.trim() || loading) {
      return;
    }


    const token =
      localStorage.getItem("meenamitra_token");


    if (!token) {

      setError("Please login first.");

      return;
    }


    const currentQuestion = question.trim();


    setMessages((previous) => [
      ...previous,

      {
        role: "user",
        content: currentQuestion,
      },
    ]);


    setQuestion("");

    setLoading(true);

    setError("");


    try {

      const response = await fetch(
        `${API_URL}/chat`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",

            Authorization: `Bearer ${token}`,
          },

          body: JSON.stringify({
            question: currentQuestion,
          }),
        }
      );


      const data = await response.json();


      if (!response.ok) {
        throw new Error(
          data.detail || "Something went wrong"
        );
      }


      setMessages((previous) => [
        ...previous,

        {
          role: "assistant",
          content: data.answer,
        },
      ]);


      loadHistory(token);


    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);

    }
  }


  // ==========================================================
  // LOGOUT
  // ==========================================================

  function logout() {

    localStorage.removeItem(
      "meenamitra_token"
    );

    setIsLoggedIn(false);

    setMessages([]);

    setHistory([]);

  }


  // ==========================================================
  // NEW CHAT
  // ==========================================================

  function newChat() {

    setMessages([]);

    setError("");

  }


  // ==========================================================
  // LOGIN / SIGNUP SCREEN
  // ==========================================================

  if (!isLoggedIn) {

    return (

      <div className="auth-page">

        <div className="auth-card">

          <div className="logo-circle">
            <Fish size={38} />
          </div>


          <h1>
            Meena<span>Mitra</span>
          </h1>


          <p className="tagline">
            Your intelligent aquaculture companion
          </p>


          <div className="ai-badge">
            <Sparkles size={15} />
            AI-powered fish farming advisor
          </div>


          <h2>
            {showSignup
              ? "Create your account"
              : "Welcome back"}
          </h2>


          <p className="auth-description">

            {showSignup
              ? "Create your MeenaMitra account to save your conversations."
              : "Sign in to continue your fish-farming journey."}

          </p>


          <form
            onSubmit={
              showSignup
                ? handleSignup
                : handleLogin
            }
          >

            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) =>
                setEmail(e.target.value)
              }
              required
            />


            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) =>
                setPassword(e.target.value)
              }
              minLength={6}
              required
            />


            {error && (
              <div className="error">
                {error}
              </div>
            )}


            <button
              className="primary-button"
              type="submit"
            >

              {showSignup
                ? "Create Account"
                : "Login"}

            </button>

          </form>


          <button
            className="switch-button"
            onClick={() => {
              setShowSignup(!showSignup);
              setError("");
            }}
          >

            {showSignup
              ? "Already have an account? Login"
              : "New to MeenaMitra? Create an account"}

          </button>

        </div>

      </div>
    );
  }


  // ==========================================================
  // MAIN CHAT SCREEN
  // ==========================================================

  return (

    <div className="app">

      {/* SIDEBAR */}

      <aside
        className={
          sidebarOpen
            ? "sidebar"
            : "sidebar closed"
        }
      >

        <div className="sidebar-header">

          <div className="brand-small">

            <div className="small-logo">
              <Fish size={22} />
            </div>

            <span>
              MeenaMitra
            </span>

          </div>


          <button
            className="icon-button"
            onClick={() =>
              setSidebarOpen(false)
            }
          >

            <X size={19} />

          </button>

        </div>


        <button
          className="new-chat-button"
          onClick={newChat}
        >

          <Plus size={18} />

          New conversation

        </button>


        <div className="history-title">

          <MessageCircle size={16} />

          Recent conversations

        </div>


        <div className="history-list">

          {history.length === 0 ? (

            <div className="empty-history">

              No conversations yet.

              <br />

              Ask MeenaMitra your first question!

            </div>

          ) : (

            history.map((item) => (

              <div
                className="history-item"
                key={item.id}
              >

                <MessageCircle size={15} />

                <span>
                  {item.question}
                </span>

              </div>

            ))

          )}

        </div>


        <div className="sidebar-bottom">

          <div className="advisor-status">

            <div className="status-dot"></div>

            MeenaMitra AI online

          </div>


          <button
            className="logout-button"
            onClick={logout}
          >

            <LogOut size={17} />

            Logout

          </button>

        </div>

      </aside>


      {/* MAIN */}

      <main className="chat-area">

        <header className="chat-header">

          {!sidebarOpen && (

            <button
              className="icon-button"
              onClick={() =>
                setSidebarOpen(true)
              }
            >

              <Menu size={22} />

            </button>

          )}


          <div>

            <h2>
              MeenaMitra
            </h2>

            <span>
              Aquaculture AI Advisor
            </span>

          </div>

        </header>


        <section className="messages">

          {messages.length === 0 ? (

            <div className="welcome">

              <div className="welcome-icon">

                <Fish size={48} />

              </div>


              <h1>
                How can I help your pond today?
              </h1>


              <p>
                Ask me about water quality, feeding,
                fish health, pond management and more.
              </p>


              <div className="suggestions">

                <button
                  onClick={() =>
                    setQuestion(
                      "What should I do if dissolved oxygen is low?"
                    )
                  }
                >

                  💧 Low dissolved oxygen

                </button>


                <button
                  onClick={() =>
                    setQuestion(
                      "How often should I feed fish in a pond?"
                    )
                  }
                >

                  🐟 Feeding schedule

                </button>


                <button
                  onClick={() =>
                    setQuestion(
                      "What are common signs of disease in farmed fish?"
                    )
                  }
                >

                  🩺 Fish health

                </button>


                <button
                  onClick={() =>
                    setQuestion(
                      "Why are fish coming to the surface early in the morning?"
                    )
                  }
                >

                  🌊 Fish behavior

                </button>

              </div>

            </div>

          ) : (

            messages.map((message, index) => (

              <div
                className={
                  message.role === "user"
                    ? "message user-message"
                    : "message assistant-message"
                }
                key={index}
              >

                <div className="message-avatar">

                  {message.role === "user"
                    ? "👩‍🌾"
                    : "🐟"}

                </div>


                <div className="message-content">

                  <div className="message-name">

                    {message.role === "user"
                      ? "You"
                      : "MeenaMitra"}

                  </div>


                  <div className="message-text">

                    {message.content}

                  </div>

                </div>

              </div>

            ))

          )}


          {loading && (

            <div className="message assistant-message">

              <div className="message-avatar">
                🐟
              </div>

              <div className="message-content">

                <div className="message-name">
                  MeenaMitra
                </div>

                <div className="typing">
                  Thinking<span>.</span>
                  <span>.</span>
                  <span>.</span>
                </div>

              </div>

            </div>

          )}

        </section>


        {error && (

          <div className="chat-error">
            {error}
          </div>

        )}


        <form
          className="chat-input-area"
          onSubmit={sendMessage}
        >

          <div className="input-wrapper">

            <textarea
              value={question}
              onChange={(e) =>
                setQuestion(e.target.value)
              }
              placeholder="Ask MeenaMitra about your fish farm..."
              rows={1}
              onKeyDown={(e) => {

                if (
                  e.key === "Enter" &&
                  !e.shiftKey
                ) {

                  e.preventDefault();

                  sendMessage(e);

                }

              }}
            />


            <button
              className="send-button"
              type="submit"
              disabled={
                loading ||
                !question.trim()
              }
            >

              <Send size={19} />

            </button>

          </div>


          <div className="disclaimer">

            MeenaMitra provides general aquaculture guidance.
            For serious fish-health problems, consult a qualified professional.

          </div>

        </form>

      </main>

    </div>
  );
}


export default App;