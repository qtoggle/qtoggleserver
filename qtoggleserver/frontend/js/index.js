/**
 * @namespace qtoggle
 */

import {globalize}     from '$qui/base/base.js'
import {gettext}       from '$qui/base/i18n.js'
import Config          from '$qui/config.js'
import * as QUI        from '$qui/index.js'
import * as Toast      from '$qui/messages/toast.js'
import * as Navigation from '$qui/navigation.js'
import * as PWA        from '$qui/pwa.js'
import * as Sections   from '$qui/sections/sections.js'
import * as HTMLUtils  from '$qui/utils/html.js'
import * as Window     from '$qui/window.js'

/* These must be imported here */
import $      from '$qui/lib/jquery.module.js'
import Logger from '$qui/lib/logger.module.js'

import * as API                   from '$app/api/api.js'
import * as AuthAPI               from '$app/api/auth.js'
import * as NotificationsAPI      from '$app/api/notifications.js'
import * as Auth                  from '$app/auth.js'
import * as Cache                 from '$app/cache.js'
import {getGlobalProgressMessage} from '$app/common/common.js'
import DashboardSection           from '$app/dashboard/dashboard-section.js'
import DevicesSection             from '$app/devices/devices-section.js'
import * as Events                from '$app/events.js'
import LoginSection               from '$app/login/login-section.js'
import PortsSection               from '$app/ports/ports-section.js'
import * as ClientSettings        from '$app/settings/client-settings.js'
import SettingsSection            from '$app/settings/settings-section.js'

import '$app/qtoggle-stock.js'


const logger = Logger.get('qtoggle')

// TODO: this is not going to be needed anymore as soon as we'll have multiple simultaneous notification messages
let initialToastShown = false


function initConfig() {
    /* Default values for qToggle-specific config  */
    Config.slavesEnabled = false
    Config.discoverEnabled = false
    Config.apiURLPrefix = ''

    /* Default values for client settings */
    ClientSettings.applyConfig()
}

function handleAccessLevelChange(oldLevel, newLevel) {
    /* Whenever access level changes, reload all required data */
    if (newLevel > AuthAPI.ACCESS_LEVEL_NONE) {
        Cache.load(newLevel, /* showModalProgress = */ true)
        /* There's no need for load().catch() since it retries indefinitely until success */
    }

    let portsSection = PortsSection.getInstance()
    let settingsSection = SettingsSection.getInstance()
    let devicesSection = Config.slavesEnabled ? DevicesSection.getInstance() : null

    portsSection.setButtonVisibility(newLevel >= AuthAPI.ACCESS_LEVEL_ADMIN)
    settingsSection.setButtonVisibility(newLevel >= AuthAPI.ACCESS_LEVEL_ADMIN)
    if (devicesSection) {
        devicesSection.setButtonVisibility(newLevel >= AuthAPI.ACCESS_LEVEL_ADMIN)
    }

    /* Notify section listeners */
    let allSections = Sections.all()
    allSections.forEach(function (section) {
        section.onAccessLevelChange(oldLevel, newLevel)
    })
}

function handleAPIEvent(event) {
}

function handlePWAUpdate() {
    logger.info('new service worker detected, updating app')

    /* Return true, indicating we're ok with the update */
    return true
}

function handlePWAInstall() {
    if (!Window.isSmallScreen()) {
        logger.debug('will not prompt to install PWA on large screen')
        return Promise.reject()
    }

    if (initialToastShown) { /* Don't spam the user with toasts */
        return Promise.reject()
    }

    let installAnchor = $('<a></a>')
    installAnchor.text(gettext('Install the app?'))
    installAnchor.on('click', function () {
        Toast.hide()
    })

    Toast.info(installAnchor)
    initialToastShown = true

    return Promise.resolve(installAnchor)
}

function initPWA() {
    try {
        PWA.enableServiceWorker(/* url = */ null, /* updateHandler = */ handlePWAUpdate)
    }
    catch (e) {
        logger.error(`failed to enable service worker: ${e}`)
    }
}

function registerSections() {
    /* Initial show call for global progress message */
    getGlobalProgressMessage().show()

    Sections.register(DashboardSection)
    Sections.register(PortsSection)
    if (Config.slavesEnabled) {
        Sections.register(DevicesSection)
    }
    Sections.register(SettingsSection)
    Sections.register(LoginSection)

    Navigation.navigateInitial().then(function () {
        /* Final hide call for global progress message */
        getGlobalProgressMessage().hide()
    })
}

function main() {
    initConfig()

    /* This must be here, before QUI.init */
    PWA.setInstallHandlers(handlePWAInstall, /* responseHandler = */ null)

    Promise.resolve()
    .then(() => QUI.init())
    .then(() => initPWA())
    .then(() => registerSections())
    .then(() => API.init())
    .then(() => Events.init())
    .then(() => Auth.init())
    .then(() => Cache.init())
    .then(function () {

        AuthAPI.addAccessLevelChangeListener(handleAccessLevelChange)
        NotificationsAPI.addEventListener(handleAPIEvent)

        let listeningInitiallyStarted = false

        Promise.all([
            Auth.whenFinalAccessLevelReady,
            PWA.isServiceWorkerSupported() ? PWA.whenServiceWorkerReady : Promise.resolve()
        ]).then(function () {
            NotificationsAPI.startListening()
            listeningInitiallyStarted = true
        })

        Window.activeChangeSignal.connect(function (active) {
            if (Config.debug) {
                return
            }

            if (active) {
                if (listeningInitiallyStarted) {
                    logger.info('application became active, (re)starting listening mechanism')

                    /* (Re)start the listening mechanism; this will, in turn, trigger a full cache reload. */
                    Cache.setReloadNeeded(/* reloadNow = */ true)
                }
            }
            else {
                logger.info('application became inactive, stopping listening mechanism')
                NotificationsAPI.stopListening()
            }
        })

        /* Warn for unset passwords */
        Cache.whenCacheReady.then(function () {

            if (!initialToastShown && /* Don't spam the user with toasts */
                AuthAPI.getCurrentAccessLevel() >= AuthAPI.ACCESS_LEVEL_ADMIN) {

                let mainDevice = Cache.getMainDevice()
                if (!mainDevice['admin_password']) {
                    let messageSpan = HTMLUtils.formatPercent(
                        gettext('Please go to %(settings)s to set an administrator password'),
                        'span',
                        {settings: Navigation.makeInternalAnchor('/settings', gettext('Settings'))}
                    )

                    Toast.warning(messageSpan)
                    initialToastShown = true
                }
            }

        })

    })
}


main()


/* Make some modules accessible globally, via window */
import('$app/api/base.js').then(globalize('qtoggle.api.base'))
import('$app/api/auth.js').then(globalize('qtoggle.api.auth'))
import('$app/api/dashboard.js').then(globalize('qtoggle.api.dashboard'))
import('$app/api/devices.js').then(globalize('qtoggle.api.devices'))
import('$app/api/master-slave.js').then(globalize('qtoggle.api.masterslave'))
import('$app/api/notifications.js').then(globalize('qtoggle.api.notifications'))
import('$app/api/ports.js').then(globalize('qtoggle.api.ports'))
import('$app/api/prefs.js').then(globalize('qtoggle.api.prefs'))
// import('$app/api/reverse.js').then(globalize('qtoggle.api.reverse'))
import('$app/auth.js').then(globalize('qtoggle.auth'))
import('$app/cache.js').then(globalize('qtoggle.cache'))
