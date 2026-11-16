---
title: "Jarvis"
description: "Our family assistant on Telegram: calendar, reminders, shopping list, recipes and weather, with the AI running at home on a ROG Ally. No data goes to cloud AI services."
draft: true
weight: 20
status: "In use"
track: "Lab"
series: ["Jarvis"]
stack: ["Python", "Telegram", "Ollama", "Qwen3 8B", "SQLite", "Google Calendar", "Tailscale", "Mealie"]
highlights:
  - "Runs entirely at home: no message or list goes to a cloud AI service"
  - "One Telegram chat for the whole family"
  - "430 automated tests and 113 evaluation cases from real conversations"
  - "Direct commands keep working when the model is down"
repo: ""
---

Jarvis is our family's assistant. It lives in Telegram and handles the routine of the house: the shared calendar, reminders, the shopping list, recipes, the weather forecast and general questions. Everything runs at home on a ROG Ally, including the AI model. No message, list or calendar entry is sent to a cloud AI service.

## What it does

- **Calendar.** Reads and creates events on the family's Google calendars.
- **Reminders.** "Remind me to pay the electricity bill on Friday at 9" becomes a scheduled reminder.
- **Shopping list.** Add, remove and compare items, including prices.
- **Recipes and meal plan.** Talks to Mealie, a self-hosted recipe manager, and can pull recipes from video links.
- **Daily summaries.** A good-morning message, a weekly overview, and heads-ups for rain and upcoming appointments.
- **Birthdays, weather and general questions.**

## How it's put together

```text
Phone (Telegram)
    │   the bot polls for messages, so no port is open to the internet
    ▼
ROG Ally (Windows)
   bot.py      receives and replies, direct commands, access control
   brain.py    talks to the model and decides which tool to use
   tools/      shopping, reminders, calendar, birthdays, weather, recipes, prices
   scheduler   fires reminders when they're due
   summaries   good morning, weekly summary, rain and appointment alerts
   data.db     SQLite: lists, reminders, history
   Ollama      qwen3:8b running locally
     │
     ├──▶ Google Calendar (the family calendars)
     ├──▶ yt-dlp: recipe video links
     └──▶ Tailscale: Mealie on a Raspberry Pi (recipes and meal plan)
```

## How a message is handled

1. The bot checks that the sender is allowed to use it.
2. The model gets the message, the recent conversation and the list of tools, and picks what to do, for example "add milk to the list".
3. The bot validates the arguments, runs the action and replies with a receipt that spells out the date, like "⏰ Reminder: pay the electricity bill, Fri 16/10 at 09:00".
4. If the model claims it did something without actually calling a tool, the bot catches it and asks the model to try again.

## Design choices

- **Private by default.** A small local model is enough for a household assistant, and it means our calendar and lists never leave the house.
- **Receipts, not "done!"** Every change is confirmed with the explicit result, so a misread date is caught on the spot instead of on the day.
- **Works without the AI.** Direct commands such as `/compras`, `/lembretes`, `/agenda`, `/semana` and `/comparar` keep working even when the model is down.
- **Tested like a product.** 430 automated tests and 113 evaluation cases built from real conversations check that the model picks the right tool before any change goes in.
- **Fails gracefully.** If the Ally goes offline, Telegram holds messages for up to 24 hours and overdue reminders fire when it comes back. The Raspberry Pi notices the outage and alerts us within 15 minutes.
- **Developed in place.** The code lives in a git repository on the Ally itself, edited and tested over SSH; my Mac only pulls a copy.

The build log for Jarvis will collect the details: picking a local model, making tool calls reliable, and what broke along the way.
