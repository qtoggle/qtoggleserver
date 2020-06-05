/**
 * @namespace qtoggle.sections
 */

import {gettext} from '$qui/base/i18n.js'
import Logger    from '$qui/lib/logger.module.js'

import StockIcon           from '$qui/icons/stock-icon.js'
import {SimpleMessageForm} from '$qui/messages/common-message-forms/common-message-forms.js'
import QUISection          from '$qui/sections/section.js'
import * as Sections       from '$qui/sections/sections.js'

import * as Auth  from '$app/auth.js'
import * as Cache from '$app/cache.js'


const LOGIN_SECTION_ID = 'login'

const logger = Logger.get('qtoggle.sections')

let sectionsList = []


/**
 * @alias qtoggle.sections.Section
 * @extends qui.sections.Section
 */
export class Section extends QUISection {

    handleRegister() {
        super.handleRegister()

        sectionsList.push(this)
    }

    preload() {
        return Cache.whenCacheReady
    }

    navigate(path) {
        if (!Auth.whenFinalAccessLevelReady.isFulfilled()) {
            /* We can't import LoginSection and use LoginSection.getInstance() here, because of circular imports */
            let loginSection = Sections.get(LOGIN_SECTION_ID)
            loginSection.setNextPath(path)

            logger.debug(`final access level not ready, navigating to login (nextPath = /${path.join('/')})`)
            return loginSection
        }

        return this
    }

    makeForbiddenMessage() {
        let icon = new StockIcon({name: 'key', variant: 'error'})
        let msg = gettext('You are not authorized to access this page!')

        return new SimpleMessageForm({
            type: 'error',
            icon: icon,
            message: msg,

            onClose() {
                Sections.showHome()
            }
        })
    }


    /* Various events */

    /**
     * Override this method to react to qToggle API events.
     * @param {qtoggle.api.notifications.Event} event the event
     */
    onServerEvent(event) {
    }

    /**
     * Override this method to react whenever qToggle access level changes.
     * @param {Number} oldLevel the old access level
     * @param {Number} newLevel the new access level
     */
    onAccessLevelChange(oldLevel, newLevel) {
    }

    /**
     * Override this method to react when frontend gets disconnected from main device.
     * @param {qtoggle.api.base.APIError} error disconnect error
     */
    onMainDeviceDisconnect(error) {
    }

    /**
     * Override this method to react when frontend reconnects to main device.
     */
    onMainDeviceReconnect() {
    }

}

/**
 * Return all registered qToggle sections.
 * @alias qtoggle.sections.all
 * @returns {qtoggle.sections.Section[]}
 */
export function all() {
    return sectionsList.slice()
}
