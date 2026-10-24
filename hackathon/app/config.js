// Deployment settings for the route planner. Committed, so no passwords here: put the broker login in
// config.local.js (gitignored), or, on the hosted page, use a broker user that can only touch the barrier topics.
window.APP_CONFIG = {
    // Our slope-aware Valhalla (hackathon/runtime/valhalla) through its Cloudflare tunnel; the address changes when
    // the tunnel container is recreated. Fallback that ignores the slope cap: "https://valhalla1.openstreetmap.de".
    valhallaUrl: "https://softball-bristol-continually-defense.trycloudflare.com",

    // Our local Coreflux broker through its Cloudflare tunnel: "wss://<random>.trycloudflare.com/mqtt", user "web"
    // (limited to access/barriers/# by lot/web_access.lotnb). Steps in hackathon/README.md, "Web app over the internet".
    brokerUrl: "wss://griffin-ray-franklin-lightbox.trycloudflare.com/mqtt",
    brokerUsername: "web",
    brokerPassword: "barackObama1234",

    // Every topic the page uses starts with this.
    topicPrefix: "access",

    // Porto, Baixa.
    center: [41.1466, -8.6110],
    zoom: 15,
};
