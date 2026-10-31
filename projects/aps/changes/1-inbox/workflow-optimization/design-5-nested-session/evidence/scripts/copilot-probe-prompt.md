You are the Foreman of a simulated batch "cop-1" (a design-5 test). You do no real work. Use `date +%T` for every timestamp and append every event to ./records.md (create it).

1. In ONE turn, start 3 Drivers D1, D2, D3 with the `task` tool in BACKGROUND mode, agent type general-purpose, model gpt-5.6-luna. Record the time each `task` call returned (does it return at once?).
   Each Driver brief: "You are Driver Dk. Run 2 rounds. A round = start ONE synchronous subagent (task tool, general-purpose, model gpt-5.6-luna) named coder-k-r that runs `sleep 40` in bash then replies 'coder done <date +%T>'. After each round, write one line `Dk round r done <date +%T>` to ./records.md. Before round 1, also try to start the coder in BACKGROUND mode once and record in ./records.md whether the tool allowed it, then continue with synchronous coders. If you receive a message, record `Dk got message <text> <date +%T>` and obey it. End with a one-line summary."
2. Right after the spawns, call `list_agents` and record what it shows.
3. Wait ~20 s with `sleep 20` in bash, then send D2 with `write_agent`: "stop after your current round". Record the time.
4. Then use `read_agent` (blocking until done) on each Driver in turn, recording when each result arrived and whether D2 obeyed.
5. Record whether any Driver could start a background coder, the maximum nesting you observed, and end with a table: Driver, rounds done, end time, obeyed message.
