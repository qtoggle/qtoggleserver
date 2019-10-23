
import {gettext} from '$qui/base/i18n.js'

import * as API   from '$app/api.js'
import * as Cache from '$app/cache.js'
import {Section}  from '$app/sections.js'

import * as Settings from './settings.js'
import SettingsForm  from './settings-form.js'


const SECTION_ID = 'settings'
const SECTION_TITLE = gettext('Settings')


export default class SettingsSection extends Section {

    constructor() {
        super({
            id: SECTION_ID,
            title: SECTION_TITLE,
            icon: Settings.WRENCH_ICON
        })

        this.settingsForm = null
    }

    load() {
        let promises = [
            Cache.whenDeviceCacheReady,
            Cache.whenPrefsCacheReady
        ]

        return Promise.all(promises)
    }

    onServerEvent(event) {
        switch (event.type) {
            case 'device-update': {
                if (this.settingsForm) {
                    this.settingsForm.updateUI()
                }

                break
            }
        }
    }

    onMainDeviceDisconnect(error) {
        if (!this.settingsForm) {
            return
        }

        if (this.settingsForm.isWaitingDeviceOffline()) {
            this.settingsForm.fulfillDeviceOffline()
        }
    }

    onMainDeviceReconnect() {
        if (!this.settingsForm) {
            return
        }

        if (this.settingsForm.isWaitingDeviceOnline()) {
            this.settingsForm.fulfillDeviceOnline()
        }
    }

    makeMainPage() {
        if (API.getCurrentAccessLevel() < API.ACCESS_LEVEL_ADMIN) {
            return
        }

        return (this.settingsForm = new SettingsForm())
    }

}
