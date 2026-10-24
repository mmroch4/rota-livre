// Deployment settings for the route planner. Committed, so no passwords here: put the broker login in
// config.local.js (gitignored), or, on the hosted page, use a broker user that can only touch the barrier topics.
window.APP_CONFIG = {
    // Pedro's Valhalla (slope-aware), exposed with a Cloudflare Tunnel, e.g. "https://xyz.trycloudflare.com".
    // For a quick test without it, the public FOSSGIS instance works (it ignores our custom slope cap):
    // "https://valhalla1.openstreetmap.de"
    valhallaUrl: "",

    // Coreflux cloud broker over secure WebSocket, from Coreflux Fleet (https://portal.coreflux.org).
    brokerUrl: "",
    brokerUsername: "",
    brokerPassword: "",

    // Every topic the page uses starts with this.
    topicPrefix: "access",

    // Porto, Baixa.
    center: [41.1466, -8.6110],
    zoom: 15,
};
