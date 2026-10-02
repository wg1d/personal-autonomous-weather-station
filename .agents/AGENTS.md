# Personal Autonomous Weather Station Rules

## Git

- Never commit things before asking.
- Always split commits in meaningful ways.
- Do not commit files that are not part of the topic treated.

## Accuracy

- Do not hallucinate, never. If something is unknown, say so.
- Every number in the book (current, accuracy, timing...) comes from a
  cited source (datasheet, manufacturer documentation) or is explicitly
  labelled as an estimate. Nothing has been measured on the prototype.
- Verify before claiming: build the firmware (`pixi run build-firmware`)
  and render the book (`pixi run book`) after any change, using the pixi
  environment so that the tool versions match the CI.

## Code

- Max line length for code is set to 80 characters.
- Every firmware file starts with a header: purpose, wiring, dependencies.
- Pins and settings are defined at the top of the file, never inline.
- Comments explain *why* (electrical reason, datasheet constraint), not
  what the line does.
- The code shown in the book must be identical to the code in the
  repository: full files are included with the `include-code-files`
  Quarto filter (`{.cpp include="..."}`), never copied by hand.

## Book

- Written in English, with a sober, factual tone: no hype words
  ("perfect", "brilliant", "massive", "flawless"...).
- One concept per chapter, in small steps: wiring, code, explanation,
  expected output, troubleshooting.
- Timestamps are always in UTC.
- Never answer a question from the chat inside the book or in code
  comments. Questions, debugging steps, bench workarounds and the reasons
  for a change belong to the conversation (or the commit message). The
  book and the comments describe the project for a reader who never saw
  the conversation: explain how things work, not how we got there.
