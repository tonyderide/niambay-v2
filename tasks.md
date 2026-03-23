# Tasks for Self-Coder

Priority order. Le selfcoder pioche ici quand il cherche du travail.

## P1 — Bugs à fixer
- [ ] daemon/collectors/process.py: test_process_collector_detects_high_cpu est flaky (dépend du CPU au moment du test)
- [ ] daemon/main.py: handle case where no collectors return events (empty list handling)

## P2 — Features à ajouter
- [ ] daemon/collectors/filesystem.py: nouveau collecteur watchdog pour détecter les fichiers modifiés
- [ ] daemon/notifications/notifier.py: ajouter historique des notifications (save/load JSON)
- [ ] daemon/brain/habits.py: ajouter day_of_week en plus de hour pour les patterns

## P3 — Améliorations code
- [ ] daemon/server/ws.py: ajouter heartbeat/ping toutes les 30s pour détecter clients morts
- [ ] daemon/config.py: ajouter validation des valeurs (port > 0, interval > 0, etc.)
- [ ] tests/: ajouter test d'intégration qui lance le daemon 5s et vérifie qu'il collecte

## P4 — Documentation
- [ ] README.md: documenter comment lancer le daemon, les modules, les endpoints
