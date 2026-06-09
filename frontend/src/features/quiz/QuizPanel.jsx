import { useMemo, useState } from 'react'
import { buildYouTubeTimestampUrl, formatTimestamp } from '../../shared/utils/time'

export function QuizPanel({
  video,
  quiz,
  onGenerate,
  isLoading,
  error,
}) {
  const [answers, setAnswers] = useState({})
  const [isChecked, setIsChecked] = useState(false)
  const [reviewFilter, setReviewFilter] = useState('all')

  const score = useMemo(() => {
    if (!quiz || !isChecked) {
      return null
    }

    const gradableQuestions = quiz.questions.filter((question) => question.options.length > 0)
    const correctCount = gradableQuestions.filter(
      (question) => answers[question.question_id] === question.correct_answer,
    ).length

    return {
      correctCount,
      totalCount: gradableQuestions.length,
      missedIds: gradableQuestions
        .filter((question) => answers[question.question_id] !== question.correct_answer)
        .map((question) => question.question_id),
      unansweredCount: quiz.questions.filter((question) => !answers[question.question_id]).length,
    }
  }, [answers, isChecked, quiz])

  const displayedQuestions = useMemo(() => {
    if (!quiz) {
      return []
    }

    if (!isChecked || reviewFilter === 'all' || !score) {
      return quiz.questions
    }

    return quiz.questions.filter((question) => score.missedIds.includes(question.question_id))
  }, [isChecked, quiz, reviewFilter, score])

  function handleSubmit(event) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    setAnswers({})
    setIsChecked(false)
    setReviewFilter('all')
    onGenerate({
      questionCount: Number(formData.get('question-count')),
      difficulty: formData.get('difficulty'),
      questionType: formData.get('question-type'),
    })
  }

  function updateAnswer(questionId, answer) {
    setAnswers((currentAnswers) => ({
      ...currentAnswers,
      [questionId]: answer,
    }))
    setIsChecked(false)
    setReviewFilter('all')
  }

  function handleCheckAnswers() {
    setIsChecked(true)
    setReviewFilter('all')
  }

  function handleRetryMissed() {
    if (!score) {
      return
    }

    setAnswers((currentAnswers) => {
      const nextAnswers = { ...currentAnswers }
      score.missedIds.forEach((questionId) => {
        delete nextAnswers[questionId]
      })
      return nextAnswers
    })
    setIsChecked(false)
    setReviewFilter('all')
  }

  function handleResetAnswers() {
    setAnswers({})
    setIsChecked(false)
    setReviewFilter('all')
  }

  if (!video) {
    return (
      <section className="quiz-panel" aria-label="Khu vực quiz">
        <h2>Quiz</h2>
        <p className="muted-text">Ingest một video trước khi tạo quiz.</p>
      </section>
    )
  }

  return (
    <section className="quiz-panel" aria-label="Khu vực quiz">
      <div className="panel-heading">
        <h2>Quiz</h2>
        <p className="muted-text">Tạo câu hỏi ôn tập từ transcript, có đáp án và timestamp nguồn.</p>
      </div>

      <form className="quiz-form" onSubmit={handleSubmit}>
        <label className="quiz-field" htmlFor="question-count">
          Số câu
          <input
            id="question-count"
            name="question-count"
            type="number"
            min="1"
            max="20"
            defaultValue="5"
            disabled={isLoading}
          />
        </label>

        <label className="quiz-field" htmlFor="difficulty">
          Độ khó
          <select id="difficulty" name="difficulty" defaultValue="medium" disabled={isLoading}>
            <option value="easy">Dễ</option>
            <option value="medium">Vừa</option>
            <option value="hard">Khó</option>
          </select>
        </label>

        <label className="quiz-field" htmlFor="question-type">
          Loại câu
          <select id="question-type" name="question-type" defaultValue="mixed" disabled={isLoading}>
            <option value="mixed">Mixed</option>
            <option value="multiple_choice">Multiple choice</option>
            <option value="true_false">True/False</option>
            <option value="short_answer">Short answer</option>
          </select>
        </label>

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Đang tạo...' : 'Tạo quiz'}
        </button>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      {quiz ? (
        <div className="quiz-result">
          <div className="answer-heading">
            <p className="question-text">
              {quiz.question_type} · {quiz.difficulty}
            </p>
            <span>{quiz.cached ? 'cached' : 'new'}</span>
          </div>

          <div className="quiz-list">
            {displayedQuestions.length === 0 ? (
              <p className="success-message">Không còn câu sai trong phần trắc nghiệm.</p>
            ) : null}

            {displayedQuestions.map((question, index) => (
              <article className="quiz-question" key={question.question_id}>
                <div className="quiz-question-heading">
                  <h3>Câu {index + 1}</h3>
                  <span>{formatQuestionType(question.question_type)}</span>
                </div>

                <p className="question-text">{question.question}</p>

                {question.options.length > 0 ? (
                  <div className="quiz-options">
                    {question.options.map((option) => (
                      <label className="quiz-option" key={option}>
                        <input
                          type="radio"
                          name={question.question_id}
                          value={option}
                          checked={answers[question.question_id] === option}
                          onChange={() => updateAnswer(question.question_id, option)}
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <textarea
                    className="quiz-short-answer"
                    rows="3"
                    value={answers[question.question_id] || ''}
                    onChange={(event) => updateAnswer(question.question_id, event.target.value)}
                    placeholder="Nhập câu trả lời ngắn để tự đối chiếu với đáp án mẫu."
                  />
                )}

                {isChecked ? (
                  <div className="quiz-feedback">
                    {question.options.length > 0 ? (
                      <p className={isCorrect(question, answers) ? 'feedback-correct' : 'feedback-wrong'}>
                        {isCorrect(question, answers) ? 'Đúng.' : 'Chưa đúng.'}
                      </p>
                    ) : (
                      <p className="muted-text">Đối chiếu câu trả lời của bạn với đáp án mẫu.</p>
                    )}
                    <p>
                      <strong>Đáp án:</strong> {question.correct_answer}
                    </p>
                    <p>{question.explanation}</p>
                  </div>
                ) : null}

                <a
                  className="source-item"
                  href={buildYouTubeTimestampUrl(video.video_id, question.source.start_seconds)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <span>{formatTimestamp(question.source.start_seconds)}</span>
                  <span>{question.source.text}</span>
                </a>
              </article>
            ))}
          </div>

          <div className="quiz-actions">
            <button type="button" onClick={handleCheckAnswers}>
              Chấm điểm
            </button>
            <button type="button" onClick={handleResetAnswers}>
              Làm lại tất cả
            </button>
            {score ? (
              <>
                <button type="button" onClick={() => setReviewFilter('missed')}>
                  Xem câu sai
                </button>
                <button type="button" onClick={() => setReviewFilter('all')}>
                  Xem tất cả
                </button>
                <button type="button" onClick={handleRetryMissed} disabled={score.missedIds.length === 0}>
                  Làm lại câu sai
                </button>
                <p className="quiz-score">
                  Điểm tự động: {score.correctCount}/{score.totalCount} câu trắc nghiệm
                  {score.unansweredCount > 0 ? ` · Chưa trả lời: ${score.unansweredCount}` : ''}
                </p>
              </>
            ) : null}
          </div>
        </div>
      ) : (
        <p className="muted-text">Chưa có quiz cho video này.</p>
      )}
    </section>
  )
}

function isCorrect(question, answers) {
  return answers[question.question_id] === question.correct_answer
}

function formatQuestionType(questionType) {
  if (questionType === 'multiple_choice') {
    return 'Multiple choice'
  }

  if (questionType === 'true_false') {
    return 'True/False'
  }

  return 'Short answer'
}
