// Where the two services live. This file is for running on your laptop with docker compose.
// On Azure, the deploy pipeline writes a new config.js with the services' Azure addresses,
// so the pages never have an address written into them.
window.SUBTRACK_CONFIG = {
  subscriptionsUrl: "http://localhost:8001",
  budgetsUrl: "http://localhost:8002",
};
