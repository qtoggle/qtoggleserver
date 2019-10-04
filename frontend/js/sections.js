
import Logger from '$qui/lib/logger.module.js'

import QUISection from '$qui/sections/section.js'
import * as Sections           from '$qui/sections/sections.js'

import * as Auth  from '$app/auth.js'
import * as Cache from '$app/cache.js'


const LOGIN_SECTION_ID = 'login'

const logger = Logger.get('qtoggle.sections')

let sectionsList = []


/**
 * @class QToggle.Sections.Section
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
            logger.debug(`final access level not ready, navigating to login (nextPath = /${path.join('/')})`)

            /* We can't import LoginSection and use LoginSection.getInstance() here, because of circular imports */
            let loginSection = Sections.get(LOGIN_SECTION_ID)
            loginSection.setNextPath(path)

            return loginSection
        }

        return this
    }


    /* Various events */

    /**
     * Override this method to react to QToggle API events.
     * @param {QToggle.API.Event} event the event
     */
    onServerEvent(event) {
    }

    /**
     * Override this method to react whenever QToggle access level changes.
     * @param {Number} oldLevel the old access level
     * @param {Number} newLevel the new access level
     */
    onAccessLevelChange(oldLevel, newLevel) {
    }

}

/**
 * Returns all registered QToggle sections.
 * @returns {QToggle.Sections.Section[]}
 */
export function all() {
    return sectionsList.slice()
}
