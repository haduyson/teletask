/**
 * PM2 Ecosystem Configuration
 * TeleTask Bot Template
 *
 * This file is auto-generated when creating a new bot.
 * Values like BOT_ID and paths will be replaced during bot creation.
 */

module.exports = {
    apps: [{
        // Bot identification
        name: 'BOT_ID_PLACEHOLDER',

        // Entry point
        script: 'bot.py',
        interpreter: 'python3.11',

        // Working directory
        cwd: '/home/botpanel/bots/BOT_ID_PLACEHOLDER',

        // Environment
        env: {
            NODE_ENV: 'production'
        },

        // Process management
        watch: false,
        autorestart: true,
        max_restarts: 10,
        restart_delay: 5000,
        kill_timeout: 3000,

        // Logging
        log_file: '/home/botpanel/logs/BOT_ID_PLACEHOLDER.log',
        error_file: '/home/botpanel/logs/BOT_ID_PLACEHOLDER-error.log',
        out_file: '/home/botpanel/logs/BOT_ID_PLACEHOLDER-out.log',
        time: true,
        log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

        // Performance
        max_memory_restart: '200M',

        // Instance
        instances: 1,
        exec_mode: 'fork'
    }]
};
