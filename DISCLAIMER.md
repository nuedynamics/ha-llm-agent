# Disclaimer

Please read this before installing LLM Agent.

**Use at your own risk.** LLM Agent is provided "as is", without warranty of any kind, under
the Apache License 2.0 (sections 7 and 8 cover the disclaimer of warranty and limitation of
liability). The authors and contributors are not liable for any damage, loss, cost or harm
that results from using it.

**AI makes mistakes.** LLM Agent lets an AI model act on your Home Assistant with
administrator rights. Depending on your settings it can switch devices, unlock locks, open
garage doors, disarm alarms, change or delete configuration, install integrations and
restart Home Assistant. AI models can misunderstand requests, make up facts and take the
wrong action. Review approval requests carefully. Do not rely on LLM Agent for safety,
security, medical or life-critical purposes.

**Prompt injection.** Text the AI reads (device names, files, web content, integration data)
can contain instructions that try to make it do something you did not ask for. LLM Agent
treats such text as data and asks for approval before risky actions in the default mode, but
no defence is perfect. Autopilot mode removes the approval step; use it only if you accept
that risk.

**Your provider, your costs, your data.** You supply your own API key. Requests, including
information about your home (entity names, states, configuration you ask about), are sent to
the AI provider you choose and are subject to that provider's terms and privacy policy. All
charges from the provider are yours. Cost figures shown in the panel are estimates from a
built-in price table and may be wrong; check your provider's billing.

**Not affiliated.** This project is independent and is not affiliated with, endorsed by or
supported by the Open Home Foundation, Home Assistant, Nabu Casa, Anthropic, OpenAI,
OpenRouter or Ollama.

**Backups.** Keep regular Home Assistant backups. LLM Agent can make a backup before some
risky actions and keeps snapshots for undo, but these do not replace your own backups.
