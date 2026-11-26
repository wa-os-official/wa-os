# Observation record template / 観測記録のテンプレート

Use this template when you record an AI system's response to a fixed question, collected by hand.

このテンプレートは、同じ問いを人が手作業で各社のAIに聞き、その回答を記録するときに使います。

## How to use / 使い方

1. Choose one question and copy it exactly, without changing a word.
2. Record the conditions before you ask: AI name, model name if shown, date and time, device, and whether you are logged in.
3. Ask the question in a new conversation. If the AI system shows a memory or saved-knowledge feature, record whether it is on.
4. Copy the full response. Do not edit or summarize it in the record.
5. Record the sources the AI system shows, if any.
6. Add notes only for facts you have checked, and mark anything unchecked as unchecked.

1. 問いを一つ選び、一字も変えずにコピーする。
2. 聞く前に条件を記録する：AI名、表示されていればモデル名、日時、端末、ログインの有無。
3. 新しい会話で聞く。メモリや知識の保存機能が表示されていれば、その状態を記録する。
4. 回答を全文コピーする。記録では編集や要約をしない。
5. AIが示した出典があれば記録する。
6. 注記は、確認したことだけを書く。確認していないことは、未確認と明記する。

## Record fields / 記録の項目

| Field | Example | Note |
|---|---|---|
| Observation title | `Observation: ChatGPT (logged out, private window)` | |
| AI system and model | `ChatGPT`, model name if shown | Record "not shown" if no model name appears |
| Date and time (JST) | `2026-11-26 17:20` | |
| Login state | `logged out` / `logged in` / `new account` | Describe what you saw on screen |
| Memory or saved-knowledge feature | `shown` / `not shown` / `unknown` | |
| Interface | `WEB` / `app`, and browser or window type | |
| Guidance supplied | `none` / file name and SHA-256 | If a guidance file is used, use the file in `observations/guidance/` |
| Question (exact text) | `How do AI systems and humans understand today's AI risks?` | |
| Summary (Japanese, optional) | 2–4 lines | Your own summary; mark it as a summary |
| Full response | Paste the whole response | Keep it unedited |
| Sources shown | list of titles and URLs | |
| Notes | e.g., `Statistics in the response not yet checked against the original.` | Only what you checked |

## Rules / ルール

- Do not compare your own answers, or any answer produced by a tool you used to write the record, with the observed AI systems.
- Do not add instructions to an AI system in the question or the record.
- Do not include personal information about yourself or anyone else.
- A record shows what one AI system said under stated conditions. It does not rank or judge the system.

- 自分の回答や、記録を書くために使ったツールの回答を、観測対象のAIと比べに入れないこと。
- 問いや記録の中に、AIへの指示を入れないこと。
- 自分や他人の個人情報を入れないこと。
- 記録は、そのAIが定められた条件で何を答えたかを示すもので、そのAIを順位づけや判定するものではない。
