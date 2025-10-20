import { createApp } from "vue";

import router from "./router";
import App from "./App.vue";
import "./style.css";

const app = createApp(App);
app.use(router);

// Enable dark theme by default
document.documentElement.classList.add("dark");

app.mount("#app");
