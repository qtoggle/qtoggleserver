
import {gettext}        from '$qui/base/i18n.js'
import {getCurrentPage} from '$qui/pages/pages.js'

import * as AuthAPI    from '$app/api/auth.js'
import * as Cache      from '$app/cache.js'
import WaitDeviceMixin from '$app/common/wait-device-mixin.js'
import {Section}       from '$app/sections.js'

import * as Settings from './settings.js'
import SettingsForm  from './settings-form.js'


const SECTION_ID = 'settings'
const SECTION_TITLE = gettext('Settings')


/**
 * @alias qtoggle.settings.SettingsSection
 * @extends qtoggle.sections.Section
 */
class SettingsSection extends Section {

    /**
     * @constructs
     */
    constructor() {
        super({
            id: SECTION_ID,
            title: SECTION_TITLE,
            icon: Settings.WRENCH_ICON,
            closeMainPageOnHide: true
        })

        this.settingsForm = null
    }

    load() {
        let promises = [
            Cache.whenDeviceCacheReady,
            Cache.whenPrefsCacheReady,
            Cache.whenProvisioningConfigsCacheReady
        ]

        return Promise.all(promises)
    }

    onServerEvent(event) {
        switch (event.type) {
            case 'device-update': {
                if (this.settingsForm && !this.settingsForm.isRebooting()) {
                    /* Don't show field changed warnings for events that are consequences of changes applied from this
                     * client (when the event is expected) */
                    let fieldChangeWarnings = !event.expected && !Settings.recentSettingsUpdateTimer.isRunning()
                    this.settingsForm.updateUI(fieldChangeWarnings)
                }

                break
            }

            case 'device-polling-update': {
                if (this.settingsForm && !this.settingsForm.isRebooting()) {
                    this.settingsForm.updateUI(/* fieldChangeWarnings = */ false)
                }

                break
            }
        }
    }

    onMainDeviceDisconnect(error) {
        let currentPage = getCurrentPage()
        if (!(currentPage instanceof WaitDeviceMixin)) {
            return
        }

        if (currentPage.isWaitingDeviceOffline()) {
            currentPage.fulfillDeviceOffline()
        }
    }

    onMainDeviceReconnect() {
        let currentPage = getCurrentPage()
        if (!(currentPage instanceof WaitDeviceMixin)) {
            return
        }

        if (currentPage.isWaitingDeviceOnline()) {
            currentPage.fulfillDeviceOnline()
        }
    }

    makeMainPage() {
        if (AuthAPI.getCurrentAccessLevel() < AuthAPI.ACCESS_LEVEL_ADMIN) {
            return this.makeForbiddenMessage()
        }

        return (this.settingsForm = new SettingsForm())
    }

}


export default SettingsSection
