
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import * as MenuBar      from '$qui/main-ui/menu-bar.js'
import * as Navigation   from '$qui/navigation.js'
import * as Sections     from '$qui/sections/sections.js'
import * as Theme        from '$qui/theme.js'
import * as PromiseUtils from '$qui/utils/promise.js'

import * as API                   from '$app/api.js'
import * as Auth                  from '$app/auth.js'
import * as Cache                 from '$app/cache.js'
import {getGlobalProgressMessage} from '$app/common/common.js'
import {Section}                  from '$app/sections.js'

import * as Login from './login.js'
import LoginForm  from './login-form.js'


const SECTION_ID = 'login'

const logger = Login.logger


/**
 * @alias qtoggle.login.LoginSection
 * @extends qtoggle.sections.Section
 */
class LoginSection extends Section {

    /**
     * @constructs
     */
    constructor() {
        super({
            id: SECTION_ID,
            title: gettext('Logout'),
            icon: Login.KEY_ICON,
            buttonType: Sections.BUTTON_TYPE_NONE
        })

        this._makeLogoutButton()
        this._nextPath = null

        Promise.all([
            Auth.whenFinalAccessLevelReady,
            Cache.whenCacheReady
        ]).then(() => this.navigateNext())
    }

    preload() {
        /* Don't call super method because we don't want to wait for cache to be ready */
        return Auth.whenInitialAccessLevelReady
    }

    navigate(path) {
        return this
    }

    /**
     * Set the path to navigate once login process is done.
     * @param {String[]} path
     */
    setNextPath(path) {
        this._nextPath = path
    }

    /**
     * Return and clear next path.
     * @returns {String[]}
     */
    popNextPath() {
        let path = this._nextPath
        this._nextPath = null

        return path
    }

    navigateNext() {
        let nextPath = this.popNextPath()
        if (nextPath != null) {
            logger.debug(`navigating to next path "/${nextPath.join('/')}"`)
            Navigation.navigate(nextPath)
        }
        else {
            Sections.showHome()
        }
    }

    _makeLogoutButton() {
        let button = $('<div></div>', {class: 'qui-base-button'})
        button.append($('<div></div>', {class: 'qui-icon'}))
        button.append($('<span></span>', {class: 'label'}))

        let iconDiv = button.find('div.qui-icon')
        let labelSpan = button.find('span.label')
        let icon = Login.KEY_ICON.alterDefault({
            variant: 'interactive',
            activeVariant: 'interactive',
            selectedVariant: 'background'
        })

        labelSpan.html(gettext('Logout'))
        icon.applyTo(iconDiv)

        button.on('click', function () {
            this._doLogout()
        }.bind(this))

        MenuBar.addButton(button)
    }

    _doLogout() {
        let progressMessage = getGlobalProgressMessage().show()
        progressMessage.setMessage(gettext('Logging out...'))

        /* Allow displaying the modal page for a short period of time */
        PromiseUtils.later(1000).then(function () {
            Auth.clearCredentials()
            window.location.href = Navigation.pathToURL([])
        })
    }

    _showAccessLevel(level) {
        let decoration = null

        switch (level) {
            case API.ACCESS_LEVEL_ADMIN:
                decoration = Theme.getVar('danger-color')
                break

            case API.ACCESS_LEVEL_NORMAL:
                decoration = Theme.getVar('interactive-color')
                break

            case API.ACCESS_LEVEL_VIEWONLY:
                decoration = Theme.getVar('disabled-color')
                break

            case API.ACCESS_LEVEL_NONE:
                break
        }

        this.setIcon(this.getIcon().alter({decoration: decoration}))
    }

    onAccessLevelChange(oldLevel, newLevel) {
        this._showAccessLevel(newLevel)
    }

    makeMainPage() {
        return new LoginForm()
    }

}


export default LoginSection
