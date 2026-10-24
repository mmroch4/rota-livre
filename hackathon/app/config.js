// Deployment settings for the route planner. Committed, so no passwords here: put the broker login in
// config.local.js (gitignored), or, on the hosted page, use a broker user that can only touch the barrier topics.
window.APP_CONFIG = {
    // The public FOSSGIS Valhalla for now: it works for Porto but ignores our slope cap.
    // Replace with Pedro's slope-aware Valhalla once it is online (e.g. through a Cloudflare Tunnel).
    valhallaUrl: "https://valhalla1.openstreetmap.de",

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
