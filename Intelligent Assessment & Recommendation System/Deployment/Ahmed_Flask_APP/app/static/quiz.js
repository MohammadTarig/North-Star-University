class QuizApp {
  constructor() {
    this.quiz = []
    this.currentQuestion = 0
    this.score = 0
    this.totalQuestions = 0
    this.selectedCategory = null

    this.initializeEventListeners()
  }

  initializeEventListeners() {
    
    document.querySelectorAll(".category-card").forEach((card) => {
      card.addEventListener("click", () => this.selectCategory(card))
    })

    
    document.getElementById("start-btn").addEventListener("click", () => this.startQuiz())

    
    document.getElementById("submit-btn").addEventListener("click", () => this.submitAnswer())

    
    document.getElementById("answer-input").addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.submitAnswer()
      }
    })

    
    document.getElementById("answer-input").addEventListener("input", (e) => {
      const value = e.target.value.toLowerCase()
      if (value && !["a", "b", "c", "d"].includes(value)) {
        e.target.value = ""
      }
    })
  }

  selectCategory(selectedCard) {
    
    document.querySelectorAll(".category-card").forEach((card) => {
      card.classList.remove("selected")
    })

    
    selectedCard.classList.add("selected")
    this.selectedCategory = selectedCard.dataset.value

   
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

    
    this.appendToChat("user", `${selectedOption}`)

    
    const isCorrect = answer === correctAnswer
    if (isCorrect) {
      this.score++
      this.appendToChat("bot", `✅ Correct! Well done!`)
    } else {
      this.appendToChat("bot", `❌ Incorrect. The correct answer was: ${correctOption}`)
    }

    
    input.value = ""

    
    this.updateScore()

    
    this.currentQuestion++

    
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
                        : "💪 Keep studying! Review the material and try again to improve your score."
                    }
                </div>
                <button class="restart-button" onclick="location.reload()">
                    🔄 Take Another Quiz
                </button>
            </div>
        `

    document.getElementById("result-box").innerHTML = resultHtml
  }

  showAlert(message, type = "info") {
    
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


document.addEventListener("DOMContentLoaded", () => {
  new QuizApp()
})


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