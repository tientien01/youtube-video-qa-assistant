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
      mode: formData.get('quiz-mode'),
      force: false,
      sourceChunkIds: [],
    })
  }

  function handleRegenerate(event) {
    const form = event.currentTarget.form
    if (!form) {
      return
    }

    const formData = new FormData(form)
    setAnswers({})
    setIsChecked(false)
    setReviewFilter('all')
    onGenerate({
      questionCount: Number(formData.get('question-count')),
      difficulty: formData.get('difficulty'),
      questionType: formData.get('question-type'),
      mode: formData.get('quiz-mode'),
      force: true,
      sourceChunkIds: [],
    })
  }

  function handleGenerateFromMissed() {
    if (!score || !quiz) {
      return
    }

    const sourceChunkIds = quiz.questions
      .filter((question) => score.missedIds.includes(question.question_id))
      .map((question) => question.source.chunk_id)

    if (sourceChunkIds.length === 0) {
      return
    }

    onGenerate({
      questionCount: Math.min(sourceChunkIds.length, 10),
      difficulty: quiz.difficulty,
      questionType: quiz.question_type,
      mode: quiz.mode || 'practice',
      force: true,
      sourceChunkIds,
    })
    setAnswers({})
    setIsChecked(false)
    setReviewFilter('all')
  }

  function handleGenerateFromSource(sourceChunkId) {
    onGenerate({
      questionCount: 3,
      difficulty: quiz?.difficulty || 'medium',
      questionType: 'mixed',
      mode: 'concept_check',
      force: true,
      sourceChunkIds: [sourceChunkId],
    })
    setAnswers({})
    setIsChecked(false)
    setReviewFilter('all')
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
      <section className="quiz-panel" aria-label="Quiz">
        <h2>Quiz</h2>
        <p className="muted-text">Select an ingested video before generating a quiz.</p>
      </section>
    )
  }

  return (
    <section className="quiz-panel" aria-label="Quiz">
      <div className="panel-heading">
        <h2>Quiz</h2>
        <p className="muted-text">Create grounded questions with explanations and timestamped sources.</p>
      </div>

      <form className="quiz-form" onSubmit={handleSubmit}>
        <label className="quiz-field" htmlFor="question-count">
          Questions
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
          Difficulty
          <select id="difficulty" name="difficulty" defaultValue="medium" disabled={isLoading}>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>

        <label className="quiz-field" htmlFor="question-type">
          Type
          <select id="question-type" name="question-type" defaultValue="mixed" disabled={isLoading}>
            <option value="mixed">Mixed</option>
            <option value="multiple_choice">Multiple choice</option>
            <option value="true_false">True/false</option>
            <option value="short_answer">Short answer</option>
          </select>
        </label>

        <label className="quiz-field" htmlFor="quiz-mode">
          Mode
          <select id="quiz-mode" name="quiz-mode" defaultValue="practice" disabled={isLoading}>
            <option value="practice">Practice</option>
            <option value="exam">Exam</option>
            <option value="concept_check">Concept check</option>
          </select>
        </label>

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate'}
        </button>
        <button type="button" onClick={handleRegenerate} disabled={isLoading}>
          Regenerate
        </button>
      </form>

      {error ? <p className="error-message">{error}</p> : null}

      {quiz ? (
        <div className="quiz-result">
          <div className="answer-heading">
            <div>
              <p className="eyebrow">Quiz setup</p>
              <p className="question-text">
                {formatQuestionType(quiz.question_type)}
                {' | '}
                {quiz.difficulty}
                {' | '}
                {quiz.mode || 'practice'}
              </p>
            </div>
            <div className="status-tags">
              <span>{quiz.cached ? 'cached' : 'new'}</span>
              {quiz.generation ? <span>{quiz.generation.generation_mode}:{quiz.generation.provider}</span> : null}
            </div>
          </div>

          {quiz.attempt_id ? <p className="muted-text">Attempt ID: {quiz.attempt_id}</p> : null}

          <div className="quiz-list">
            {displayedQuestions.length === 0 ? (
              <p className="success-message">No missed multiple-choice or true/false questions remain.</p>
            ) : null}

            {displayedQuestions.map((question, index) => (
              <article className="quiz-question" key={question.question_id}>
                <div className="quiz-question-heading">
                  <h3>Question {index + 1}</h3>
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
                    placeholder="Write a short answer, then compare it with the sample answer."
                  />
                )}

                {isChecked ? (
                  <div className="quiz-feedback">
                    {question.options.length > 0 ? (
                      <p className={isCorrect(question, answers) ? 'feedback-correct' : 'feedback-wrong'}>
                        {isCorrect(question, answers) ? 'Correct.' : 'Not yet.'}
                      </p>
                    ) : (
                      <p className="muted-text">Compare your answer with the sample answer.</p>
                    )}
                    <p>
                      <strong>Answer:</strong> {question.correct_answer}
                    </p>
                    <p>{question.explanation}</p>
                  </div>
                ) : null}

                <div className="quiz-source-row">
                  <a
                    className="source-item"
                    href={buildYouTubeTimestampUrl(video.video_id, question.source.start_seconds)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>{formatTimestamp(question.source.start_seconds)}</span>
                    <span>{question.source.text}</span>
                  </a>
                  <button
                    className="quiz-source-action"
                    type="button"
                    onClick={() => handleGenerateFromSource(question.source.chunk_id)}
                  >
                    Generate from source
                  </button>
                </div>
              </article>
            ))}
          </div>

          <div className="quiz-actions">
            <button type="button" onClick={handleCheckAnswers}>
              Check answers
            </button>
            <button type="button" onClick={handleResetAnswers}>
              Reset
            </button>
            {score ? (
              <>
                <button type="button" onClick={() => setReviewFilter('missed')}>
                  Show missed
                </button>
                <button type="button" onClick={() => setReviewFilter('all')}>
                  Show all
                </button>
                <button type="button" onClick={handleRetryMissed} disabled={score.missedIds.length === 0}>
                  Retry missed
                </button>
                <button type="button" onClick={handleGenerateFromMissed} disabled={score.missedIds.length === 0}>
                  Quiz from missed
                </button>
                <p className="quiz-score">
                  Score: {score.correctCount}/{score.totalCount}
                  {score.unansweredCount > 0 ? ` | Unanswered: ${score.unansweredCount}` : ''}
                </p>
              </>
            ) : null}
          </div>
        </div>
      ) : (
        <p className="muted-text">No quiz yet for this video.</p>
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
    return 'True/false'
  }

  if (questionType === 'mixed') {
    return 'Mixed'
  }

  return 'Short answer'
}
