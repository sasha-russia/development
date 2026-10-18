"use client";

import { useState } from "react";
import type { Question } from "@/lib/news";

export default function Quiz({ questions }: { questions: Question[] }) {
  const [picked, setPicked] = useState<(number | null)[]>(() => questions.map(() => null));
  const answered = picked.filter((p) => p !== null).length;
  const score = picked.filter((p, i) => p === questions[i].answer).length;

  function choose(q: number, option: number) {
    setPicked((prev) => prev.map((p, i) => (i === q && p === null ? option : p)));
  }

  return (
    <div className="quiz">
      {questions.map((question, q) => {
        const choice = picked[q];
        return (
          <fieldset key={question.text} className="quiz-question">
            <legend>
              {question.text}{" "}
              <span className="quiz-count">
                {q + 1}/{questions.length}
              </span>
            </legend>
            <div className="quiz-options">
              {question.options.map((option, o) => {
                let state = "";
                if (choice !== null) {
                  if (o === question.answer) state = "is-right";
                  else if (o === choice) state = "is-wrong";
                }
                return (
                  <button
                    key={option}
                    type="button"
                    className={`quiz-option ${state}`}
                    onClick={() => choose(q, o)}
                    disabled={choice !== null}
                    aria-pressed={choice === o}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
            {choice !== null && (
              <p className="quiz-explanation" role="status">
                <strong>{choice === question.answer ? "Верно." : "Нет."}</strong>{" "}
                {question.explanation}
              </p>
            )}
          </fieldset>
        );
      })}
      {answered === questions.length && (
        <div className="quiz-result" role="status">
          <p className="quiz-score">
            {score} из {questions.length}
          </p>
          <p>
            {score === questions.length
              ? "Вы знаете город лучше, чем мы."
              : "Неплохо. Самое время прогуляться по набережной."}
          </p>
          <button
            type="button"
            className="quiz-retry"
            onClick={() => setPicked(questions.map(() => null))}
          >
            Пройти ещё раз
          </button>
        </div>
      )}
    </div>
  );
}
