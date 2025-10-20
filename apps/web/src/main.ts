import { createApp } from "vue";
import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";

import router from "./router";
import App from "./App.vue";
import Menubar from "./components/ui/Menubar.vue";
import "./style.css";

const app = createApp(App);
app.use(router);
app.use(PrimeVue, {
  theme: {
    preset: Aura,
  },
});

// Register global components
app.component("Menubar", Menubar);

app.mount("#app");
