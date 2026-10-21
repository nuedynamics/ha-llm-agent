# Scheduled prompts
> Run a request to this agent on a schedule or event (llm_agent.ask in an automation) and send the answer as a notification.

A scheduled prompt is an ordinary automation that calls the `llm_agent.ask` action,
keeps the answer with `response_variable`, then sends it somewhere. Create it like any
other automation (see the automations page); the household approves it once.

```yaml
alias: "Weekly battery check"
triggers:
  - trigger: time
    at: "18:00:00"
conditions:
  - condition: time
    weekday: [sun]
actions:
  - action: llm_agent.ask
    data:
      title: "Weekly battery check"
      prompt: >-
        List devices that are unavailable and batteries under 20%, with the area of
        each. If everything is fine, say so in one line.
    response_variable: answer
  - action: persistent_notification.create
    data:
      title: "Weekly battery check"
      message: "{{ answer.response }}"
mode: single
```

- To reach a phone, use the household's `notify.mobile_app_<device>` action
  (`message: "{{ answer.response }}"`). Look up which notify actions exist first.
- Any trigger works: a time, sunset, a person arriving home, a sensor changing.
- `title` names the chat in the AI panel, where every run can be read in full. Without it
  the chat is named after the start of the prompt.
- `answer.conversation_id` can be passed back as `conversation_id` to continue the same
  chat on the next run, but every run then adds to one ever-growing chat. Prefer a new
  chat per run.
- Nobody can approve anything while an automation runs, so any action that would ask the
  household is refused. Scheduled prompts are for reading and reporting. For a change
  on a schedule, put the change itself in the automation's actions.
- Write the prompt so the answer stands on its own in a notification: say what to check,
  what to leave out and how short to be.
- Each run costs one request to the model. Avoid frequent triggers (every few minutes,
  or on a sensor that changes often).
