import { useEffect, useState } from "react";

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
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


function App() {
  // ==========================================================
  // STATE
  // ==========================================================

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

  // Currently selected conversation
  const [activeHistoryId, setActiveHistoryId] = useState(null);

  // Current conversation UUID
  const [conversationId, setConversationId] = useState(null);


  // ==========================================================
  // SAVE AUTH SESSION
  // ==========================================================

  function saveAuthSession(data) {
    if (data.access_token) {
      localStorage.setItem(
        "meenamitra_token",
        data.access_token
      );
    }

    if (data.refresh_token) {
      localStorage.setItem(
        "meenamitra_refresh_token",
        data.refresh_token
      );
    }

    if (data.email) {
      localStorage.setItem(
        "meenamitra_email",
        data.email
      );
    }
  }


  // ==========================================================
  // CLEAR AUTH SESSION
  // ==========================================================

  function clearAuthSession() {
    localStorage.removeItem(
      "meenamitra_token"
    );

    localStorage.removeItem(
      "meenamitra_refresh_token"
    );

    localStorage.removeItem(
      "meenamitra_email"
    );
  }


  // ==========================================================
  // REFRESH ACCESS TOKEN
  // ==========================================================

  async function refreshAccessToken() {
    const refreshToken =
      localStorage.getItem(
        "meenamitra_refresh_token"
      );

    if (!refreshToken) {
      return null;
    }

    try {
      const response = await fetch(
        `${API_URL}/refresh`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            refresh_token: refreshToken,
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        clearAuthSession();
        return null;
      }

      saveAuthSession(data);

      return data.access_token;
    }

    catch (err) {
      console.error(
        "Token refresh error:",
        err
      );

      return null;
    }
  }


  // ==========================================================
  // AUTHENTICATED FETCH
  //
  // Automatically retries once after
  // an expired access token.
  // ==========================================================

  async function authenticatedFetch(
    url,
    options = {}
  ) {
    let token =
      localStorage.getItem(
        "meenamitra_token"
      );

    if (!token) {
      throw new Error(
        "Please login first."
      );
    }

    const firstOptions = {
      ...options,

      headers: {
        ...(options.headers || {}),

        Authorization:
          `Bearer ${token}`,
      },
    };

    let response =
      await fetch(
        url,
        firstOptions
      );

    // --------------------------------------------------------
    // ACCESS TOKEN EXPIRED
    // --------------------------------------------------------

    if (response.status === 401) {
      const newToken =
        await refreshAccessToken();

      if (!newToken) {
        throw new Error(
          "Your session has expired. Please login again."
        );
      }

      const retryOptions = {
        ...options,

        headers: {
          ...(options.headers || {}),

          Authorization:
            `Bearer ${newToken}`,
        },
      };

      response =
        await fetch(
          url,
          retryOptions
        );
    }

    return response;
  }


  // ==========================================================
  // RESTORE SESSION ON PAGE LOAD
  // ==========================================================

  useEffect(() => {
    async function restoreSession() {
      const token =
        localStorage.getItem(
          "meenamitra_token"
        );

      const refreshToken =
        localStorage.getItem(
          "meenamitra_refresh_token"
        );

      // Nothing stored
      if (!token && !refreshToken) {
        return;
      }

      // --------------------------------------------------------
      // First try existing access token
      // --------------------------------------------------------

      if (token) {
        try {
          const response =
            await fetch(
              `${API_URL}/history`,
              {
                headers: {
                  Authorization:
                    `Bearer ${token}`,
                },
              }
            );

          if (response.ok) {
            setIsLoggedIn(true);

            const data =
              await response.json();

            setHistory(
              Array.isArray(
                data.history
              )
                ? data.history
                : []
            );

            return;
          }
        }

        catch (err) {
          console.error(
            "Session check error:",
            err
          );
        }
      }

      // --------------------------------------------------------
      // Existing token failed.
      // Try refresh token.
      // --------------------------------------------------------

      if (refreshToken) {
        const newToken =
          await refreshAccessToken();

        if (newToken) {
          setIsLoggedIn(true);

          await loadHistory(
            newToken
          );

          return;
        }
      }

      // --------------------------------------------------------
      // Both tokens failed.
      // --------------------------------------------------------

      clearAuthSession();

      setIsLoggedIn(false);
    }

    restoreSession();
  }, []);


  // ==========================================================
  // SIGNUP
  // ==========================================================

  async function handleSignup(e) {
    e.preventDefault();

    setError("");

    try {
      const response =
        await fetch(
          `${API_URL}/signup`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              email,
              password,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Signup failed"
        );
      }

      // --------------------------------------------------------
      // If backend returned session immediately
      // --------------------------------------------------------

      if (data.access_token) {
        saveAuthSession(data);

        setIsLoggedIn(true);

        setEmail("");

        setPassword("");

        setMessages([]);

        setConversationId(null);

        setActiveHistoryId(null);

        await loadHistory(
          data.access_token
        );
      }

      // --------------------------------------------------------
      // Email confirmation required
      // --------------------------------------------------------

      else {
        setError(
          "Signup successful. Please check your email to confirm your account, then login."
        );

        setShowSignup(false);
      }
    }

    catch (err) {
      setError(
        err.message ||
        "Signup failed"
      );
    }
  }


  // ==========================================================
  // LOGIN
  // ==========================================================

  async function handleLogin(e) {
    e.preventDefault();

    setError("");

    try {
      const response =
        await fetch(
          `${API_URL}/login`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              email,
              password,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Login failed"
        );
      }

      saveAuthSession(data);

      setIsLoggedIn(true);

      setMessages([]);

      setConversationId(null);

      setActiveHistoryId(null);

      setPassword("");

      await loadHistory(
        data.access_token
      );
    }

    catch (err) {
      setError(
        err.message ||
        "Login failed"
      );
    }
  }


  // ==========================================================
  // LOAD HISTORY
  // ==========================================================

  async function loadHistory(
    token = null
  ) {
    try {
      let response;

      if (token) {
        response =
          await fetch(
            `${API_URL}/history`,
            {
              headers: {
                Authorization:
                  `Bearer ${token}`,
              },
            }
          );
      }

      else {
        response =
          await authenticatedFetch(
            `${API_URL}/history`
          );
      }

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Could not load chat history"
        );
      }

      setHistory(
        Array.isArray(
          data.history
        )
          ? data.history
          : []
      );
    }

    catch (err) {
      console.error(
        "History loading error:",
        err
      );
    }
  }


  // ==========================================================
  // OPEN OLD CONVERSATION
  // ==========================================================

  function openHistoryChat(conversation) {
    if (!conversation) {
      return;
    }

    // --------------------------------------------------------
    // Set the selected conversation
    // --------------------------------------------------------

    setConversationId(
      conversation.conversation_id
    );

    setActiveHistoryId(
      conversation.conversation_id
    );

    setError("");

    // --------------------------------------------------------
    // Restore every message in the conversation
    // --------------------------------------------------------

    const restoredMessages = [];

    const conversationMessages =
      Array.isArray(
        conversation.messages
      )
        ? conversation.messages
        : [];

    // Backend returns newest first.
    // Reverse it so chat displays oldest → newest.
    conversationMessages
      .slice()
      .reverse()
      .forEach((item) => {
        restoredMessages.push({
          role: "user",
          content: item.question,
        });

        restoredMessages.push({
          role: "assistant",
          content: item.answer,
        });
      });

    setMessages(
      restoredMessages
    );

    // On smaller screens, close sidebar
    setSidebarOpen(false);
  }


  // ==========================================================
  // SEND MESSAGE
  // ==========================================================

  async function sendMessage(e) {
    e.preventDefault();

    if (
      !question.trim() ||
      loading
    ) {
      return;
    }

    const token =
      localStorage.getItem(
        "meenamitra_token"
      );

    if (!token) {
      setError(
        "Please login first."
      );

      return;
    }

    const currentQuestion =
      question.trim();

    // --------------------------------------------------------
    // Immediately show user message
    // --------------------------------------------------------

    setMessages(
      previous => [
        ...previous,

        {
          role: "user",
          content:
            currentQuestion,
        },
      ]
    );

    setQuestion("");

    setLoading(true);

    setError("");

    try {
      // ------------------------------------------------------
      // IMPORTANT:
      // Send the CURRENT conversation ID.
      //
      // null = create a new conversation
      // UUID = continue existing conversation
      // ------------------------------------------------------

      const response =
        await authenticatedFetch(
          `${API_URL}/chat`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              question:
                currentQuestion,

              access_token:
                token,

              conversation_id:
                conversationId,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "Something went wrong"
        );
      }

      // ------------------------------------------------------
      // Backend creates conversation ID for first question.
      // Save it for every future question.
      // ------------------------------------------------------

      if (data.conversation_id) {
        setConversationId(
          data.conversation_id
        );

        setActiveHistoryId(
          data.conversation_id
        );
      }

      // ------------------------------------------------------
      // Show AI response in SAME chat
      // ------------------------------------------------------

      setMessages(
        previous => [
          ...previous,

          {
            role: "assistant",
            content:
              data.answer,
          },
        ]
      );

      // ------------------------------------------------------
      // Reload sidebar.
      //
      // IMPORTANT:
      // We DO NOT reset conversationId here.
      // ------------------------------------------------------

      await loadHistory();
    }

    catch (err) {
      console.error(
        "Chat error:",
        err
      );

      setError(
        err.message ||
        "Unable to get response"
      );
    }

    finally {
      setLoading(false);
    }
  }


  // ==========================================================
  // LOGOUT
  // ==========================================================

  function logout() {
    clearAuthSession();

    setIsLoggedIn(false);

    setMessages([]);

    setHistory([]);

    setConversationId(null);

    setActiveHistoryId(null);

    setQuestion("");

    setEmail("");

    setPassword("");

    setError("");
  }


  // ==========================================================
  // NEW CONVERSATION
  // ==========================================================

  function newChat() {
    // --------------------------------------------------------
    // THIS IS VERY IMPORTANT
    //
    // Setting conversationId to null tells the backend:
    // "The next question is a brand-new conversation."
    // --------------------------------------------------------

    setConversationId(null);

    setActiveHistoryId(null);

    setMessages([]);

    setQuestion("");

    setError("");

    setSidebarOpen(false);
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
              onChange={e =>
                setEmail(
                  e.target.value
                )
              }
              required
            />

            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={e =>
                setPassword(
                  e.target.value
                )
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
              setShowSignup(
                !showSignup
              );

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
  // MAIN APPLICATION
  // ==========================================================

  return (
    <div className="app">

      {/* ======================================================
          SIDEBAR
      ====================================================== */}

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


        {/* NEW CONVERSATION */}

        <button
          className="new-chat-button"
          onClick={newChat}
        >
          <Plus size={18} />

          New conversation
        </button>


        {/* HISTORY TITLE */}

        <div className="history-title">

          <MessageCircle size={16} />

          Recent conversations

        </div>


        {/* HISTORY LIST */}

        <div className="history-list">

          {history.length === 0 ? (

            <div className="empty-history">

              No conversations yet.

              <br />

              Ask MeenaMitra your first question!

            </div>

          ) : (

            history.map(
              (conversation) => (

                <button
                  type="button"

                  key={
                    conversation.conversation_id
                  }

                  className={
                    activeHistoryId ===
                    conversation.conversation_id
                      ? "history-item active"
                      : "history-item"
                  }

                  onClick={() =>
                    openHistoryChat(
                      conversation
                    )
                  }
                >

                  <MessageCircle
                    size={15}
                  />

                  <span>

                    {conversation.title ||
  (conversation.messages?.length > 0
    ? conversation.messages[0].question
    : "Conversation")}

                  </span>

                </button>

              )
            )

          )}

        </div>


        {/* SIDEBAR BOTTOM */}

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


      {/* ======================================================
          MAIN CHAT
      ====================================================== */}

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


        {/* ====================================================
            MESSAGES
        ==================================================== */}

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
                Ask me about water quality,
                feeding, fish health,
                pond management and more.
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

            messages.map(
              (message, index) => (

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

              )
            )

          )}


          {/* LOADING */}

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
                  Thinking
                  <span>.</span>
                  <span>.</span>
                  <span>.</span>
                </div>

              </div>

            </div>

          )}

        </section>


        {/* ERROR */}

        {error && (

          <div className="chat-error">
            {error}
          </div>

        )}


        {/* ====================================================
            CHAT INPUT
        ==================================================== */}

        <form
          className="chat-input-area"
          onSubmit={sendMessage}
        >

          <div className="input-wrapper">

            <textarea

              value={question}

              onChange={e =>
                setQuestion(
                  e.target.value
                )
              }

              placeholder="Ask MeenaMitra about your fish farm..."

              rows={1}

              onKeyDown={e => {

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