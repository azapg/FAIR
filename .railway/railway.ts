import {
  defineRailway,
  github,
  preserve,
  project,
  service,
  volume,
} from "railway/iac";

export default defineRailway(() => {
  const data = volume("fair-platform-volume", {
    region: "us-east4-eqdc4a",
    sizeMB: 5000,
  });

  const app = service("fair-platform", {
    source: github("azapg/FAIR", {
      branch: "canary",
    }),
    healthcheck: "/health",
    healthcheckTimeout: 300,
    replicas: 1,
    volumeMounts: {
      "/data": data,
    },
    env: {
      DATABASE_URL: "sqlite:////data/fair.db",
      FAIR_ADMISSION_MODE: "invite_only",
      FAIR_AI_CONTROLS_ENABLED: "false",
      FAIR_API_BASE_URL: preserve(),
      FAIR_AUTO_MIGRATE: "1",
      FAIR_BASE_URL: preserve(),
      FAIR_BOOTSTRAP_ADMIN_EMAIL: preserve(),
      FAIR_BOOTSTRAP_ADMIN_NAME: preserve(),
      FAIR_CORS_ORIGINS: preserve(),
      FAIR_DATA_DIR: "/data",
      FAIR_DEPLOYMENT_MODE: "COMMUNITY",
      FAIR_EMAIL_ENABLED: preserve(),
      FAIR_EMAIL_SENDER: preserve(),
      FAIR_ENFORCE_EMAIL_VERIFICATION: "1",
      FAIR_RESEND_API_KEY: preserve(),
      FAIR_SESSION_COOKIE_SECURE: "1",
      FAIR_STORAGE_BACKEND: "local",
      RAILWAY_HEALTHCHECK_TIMEOUT_SEC: "300",
      SECRET_KEY: preserve(),
    },
  });

  return project("fairgrade-platform", {
    resources: [app, data],
  });
});
