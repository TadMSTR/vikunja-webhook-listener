// PM2 process definition for forge. start.sh sources secrets from ~/.secrets/ at runtime —
// no secret ever lives in this file (it is committed to git).
module.exports = {
  apps: [{
    name: "vikunja-webhook-listener",
    script: "start.sh",
    interpreter: "bash",
    cwd: "/home/ted/repos/personal/vikunja-webhook-listener",
    restart_delay: 5000,
    max_restarts: 10,
    watch: false,
  }]
};
