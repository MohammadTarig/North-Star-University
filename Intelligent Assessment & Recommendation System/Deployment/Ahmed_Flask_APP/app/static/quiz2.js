class QuizApp {
  constructor() {
    this.quiz = []
    this.currentQuestion = 0
    this.score = 0
    this.totalQuestions = 0
    this.selectedCategory = null
    this.studentAnswers = [] 

    this.initializeEventListeners()
  }

  initializeEventListeners() {
    // Category selection
    document.querySelectorAll(".category-card").forEach((card) => {
      card.addEventListener("click", () => this.selectCategory(card))
    })

    // Start quiz button
    document.getElementById("start-btn").addEventListener("click", () => this.startQuiz())

    // Submit answer button
    document.getElementById("submit-btn").addEventListener("click", () => this.submitAnswer())

    // Enter key for answer input
    document.getElementById("answer-input").addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.submitAnswer()
      }
    })

    // Input validation
    document.getElementById("answer-input").addEventListener("input", (e) => {
      const value = e.target.value.toLowerCase()
      if (value && !["a", "b", "c", "d"].includes(value)) {
        e.target.value = ""
      }
    })
  }

  selectCategory(selectedCard) {
    // Remove previous selection
    document.querySelectorAll(".category-card").forEach((card) => {
      card.classList.remove("selected")
    })

    // Add selection to clicked card
    selectedCard.classList.add("selected")
    this.selectedCategory = selectedCard.dataset.value

    // Enable start button
    document.getElementById("start-btn").disabled = false
  }

  async startQuiz() {
    if (!this.selectedCategory) {
      this.showAlert("Please select a category first!", "warning")
      return
    }

    try {
      this.showLoading(true)

      const response = await fetch("/api/start_quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: this.selectedCategory }),
      })

      const data = await response.json()

      if (data.success) {
        this.quiz = data.quiz.questions
        this.totalQuestions = this.quiz.length
        this.currentQuestion = 0
        this.score = 0
        this.studentAnswers = [] // Reset student answers

        this.showQuizInterface()
        this.askNextQuestion()
      } else {
        this.showAlert("Failed to load quiz. Please try again.", "error")
      }
    } catch (error) {
      console.error("Error starting quiz:", error)
      this.showAlert("Network error. Please check your connection.", "error")
    } finally {
      this.showLoading(false)
    }
  }

  showQuizInterface() {
    document.getElementById("quiz-setup").style.display = "none"
    document.getElementById("quiz-interface").style.display = "block"
    document.getElementById("result-box").innerHTML = ""

    // Clear chat box except welcome message
    const chatBox = document.getElementById("chat-box")
    chatBox.innerHTML = `
            <div class="welcome-message">
                <div class="bot-avatar">🤖</div>
                <div class="message-content">
                    <p>Welcome to the ${this.getCategoryDisplayName()} quiz! I'll ask you ${this.totalQuestions} questions. Answer with a, b, c, or d. Good luck! 🚀</p>
                </div>
            </div>
        `

    this.updateProgress()
    this.updateScore()
  }

  getCategoryDisplayName() {
    const categoryMap = {
      Cybersecurity: "Linux Basics for Hackers",
      ArtificialIntelligence: "AI Basics and fundamentals",
      WebDevelopment: "Web development Basics for beginners",
    }
    return categoryMap[this.selectedCategory] || this.selectedCategory
  }

  askNextQuestion() {
    if (this.currentQuestion >= this.quiz.length) {
      this.finishQuiz()
      return
    }

    const question = this.quiz[this.currentQuestion]
    const questionHtml = `
            <div class="question-content">
                <div class="question-title">Question ${this.currentQuestion + 1}:</div>
                <p>${question.question}</p>
                <ul class="options-list">
                    ${question.options.map((option) => `<li>${option}</li>`).join("")}
                </ul>
            </div>
        `

    this.appendToChat("bot", questionHtml)
    this.updateProgress()

    // Focus on input
    setTimeout(() => {
      document.getElementById("answer-input").focus()
    }, 100)
  }

  submitAnswer() {
    const input = document.getElementById("answer-input")
    const answer = input.value.trim().toLowerCase()

    if (!answer) {
      this.showAlert("Please enter an answer!", "warning")
      return
    }

    if (!["a", "b", "c", "d"].includes(answer)) {
      this.showAlert("Please enter a, b, c, or d only.", "warning")
      return
    }

    const question = this.quiz[this.currentQuestion]
    const correctAnswer = question.right_option.toLowerCase()
    const selectedOption = question.options.find((opt) => opt.toLowerCase().startsWith(answer + "."))
    const correctOption = question.options.find((opt) => opt.toLowerCase().startsWith(correctAnswer + "."))

    // Store student answer for backend evaluation
    this.studentAnswers.push({
      questionIndex: this.currentQuestion,
      studentAnswer: answer,
      question: question.question,
      rightOption: question.right_option,
    })

    // Show user's answer
    this.appendToChat("user", `${selectedOption}`)

    // Check if correct and show feedback
    const isCorrect = answer === correctAnswer
    if (isCorrect) {
      this.score++
    //   this.appendToChat("bot", `✅ Correct! Well done!`)
    } else {
    //   this.appendToChat("bot", `❌ Incorrect. The correct answer was: ${correctOption}`)
    }

    // Clear input
    input.value = ""

    // Update score display
    this.updateScore()

    // Move to next question
    this.currentQuestion++

    // Small delay before next question
    setTimeout(() => {
      this.askNextQuestion()
    }, 1500)
  }

  appendToChat(sender, content) {
    const chatBox = document.getElementById("chat-box")
    const messageDiv = document.createElement("div")
    messageDiv.className = `chat-msg ${sender}`

    if (sender === "bot") {
      messageDiv.innerHTML = `
                <div class="bot-avatar">🤖</div>
                <div class="message-content">${content}</div>
            `
    } else {
      messageDiv.innerHTML = `
                <div class="user-avatar">👤</div>
                <div class="message-content">${content}</div>
            `
    }

    chatBox.appendChild(messageDiv)
    chatBox.scrollTop = chatBox.scrollHeight
  }

  updateProgress() {
    const progressFill = document.getElementById("progress-fill")
    const progressText = document.getElementById("progress-text")

    const percentage = (this.currentQuestion / this.totalQuestions) * 100
    progressFill.style.width = `${percentage}%`
    progressText.textContent = `Question ${this.currentQuestion + 1} of ${this.totalQuestions}`
  }

  updateScore() {
    document.getElementById("current-score").textContent = `Score: ${this.score}`
  }

  finishQuiz() {
    document.getElementById("quiz-interface").style.display = "none"

    // Show loading state
    document.getElementById("result-box").innerHTML = `
      <div class="result-card">
        <div class="result-icon">⏳</div>
        <h2 class="result-title">Evaluating Your Quiz...</h2>
        <div class="result-message">
          Please wait while we analyze your answers and provide detailed feedback.
        </div>
      </div>
    `

    // Prepare payload for backend evaluation
    const payload = {
      questions: this.quiz.map((q, index) => {
        const studentAnswer = this.studentAnswers.find((sa) => sa.questionIndex === index)
        return {
          question: q.question,
          right_option: q.right_option,
          student_answer: studentAnswer ? studentAnswer.studentAnswer : null,
          options: q.options,
        }
      }),
      category: this.selectedCategory,
      totalQuestions: this.totalQuestions,
    }

    fetch("/api/evaluate_quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`)
        }
        return res.json()
      })
      .then((data) => {
        if (data.success) {
          const result = data.result
          const resultHtml = `
            <div class="result-card">
              <div class="result-icon">${result.passed ? "🎉" : "📚"}</div>
              <h2 class="result-title">Quiz Complete!</h2>
              <div class="result-score ${result.passed ? "result-pass" : "result-fail"}">
                ${result.score}
              </div>
              <div class="result-message">
                ${result.feedback}
              </div>
              <div class="result-actions">
                <button class="restart-button" onclick="location.reload()">
                  🔄 Take Another Quiz
                </button>
              </div>
            </div>
          `
          document.getElementById("result-box").innerHTML = resultHtml
        } else {
          this.showAlert("Failed to evaluate quiz. Please try again.", "error")
          // Fallback to local evaluation
          this.showLocalResults()
        }
      })
      .catch((err) => {
        console.error("Error during quiz evaluation:", err)
        this.showAlert("Network error during evaluation. Showing local results.", "warning")
        // Fallback to local evaluation
        this.showLocalResults()
      })
  }

  // Add fallback method for local results
  showLocalResults() {
    const percentage = (this.score / this.totalQuestions) * 100
    const passed = percentage >= 60

    const resultHtml = `
      <div class="result-card">
        <div class="result-icon">${passed ? "🎉" : "📚"}</div>
        <h2 class="result-title">Quiz Complete!</h2>
        <div class="result-score ${passed ? "result-pass" : "result-fail"}">
          ${this.score}/${this.totalQuestions} (${Math.round(percentage)}%)
        </div>
        <div class="result-message">
          ${
            passed
              ? "🎊 Congratulations! You passed the quiz. Great job mastering the material!"
              : "💪 Keep studying! Review the material and try again to improve your score. (L)(O)(C)(L)"
          }
        </div>
        <div class="result-actions">
          <button class="restart-button" onclick="location.reload()">
            🔄 Take Another Quiz
          </button>
        </div>
      </div>
    `
    document.getElementById("result-box").innerHTML = resultHtml
  }

  showAlert(message, type = "info") {
    // Create a simple alert system
    const alertDiv = document.createElement("div")
    alertDiv.className = `alert alert-${type}`
    alertDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideInRight 0.3s ease;
            max-width: 300px;
        `

    switch (type) {
      case "error":
        alertDiv.style.background = "#ef4444"
        break
      case "warning":
        alertDiv.style.background = "#f59e0b"
        break
      default:
        alertDiv.style.background = "#3b82f6"
    }

    alertDiv.textContent = message
    document.body.appendChild(alertDiv)

    setTimeout(() => {
      alertDiv.remove()
    }, 3000)
  }

  showLoading(show) {
    const startBtn = document.getElementById("start-btn")
    if (show) {
      startBtn.innerHTML = "<span>🔄 Loading...</span>"
      startBtn.disabled = true
    } else {
      startBtn.innerHTML = "<span>🚀 Start Quiz</span>"
      startBtn.disabled = false
    }
  }
}

// Initialize the quiz app when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  new QuizApp()
})

// Add CSS animation for alerts
const style = document.createElement("style")
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`
document.head.appendChild(style)
