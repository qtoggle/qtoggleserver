
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import * as MenuBar      from '$qui/main-ui/menu-bar.js'
import * as Navigation   from '$qui/navigation.js'
import * as Sections     from '$qui/sections/sections.js'
import * as Theme        from '$qui/theme.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as Window       from '$qui/window.js'

import * as API                   from '$app/api.js'
import * as Auth                  from '$app/auth.js'
import {getGlobalProgressMessage} from '$app/common/common.js'
import {Section}                  from '$app/sections.js'

import * as Login from './login.js'
import LoginForm  from './login-form.js'


const SECTION_ID = 'login'

const logger = Login.logger


export default class LoginSection extends Section {

    constructor() {
        super({
            id: SECTION_ID,
            title: gettext('Logout'),
            icon: Login.KEY_ICON,
            buttonType: Sections.BUTTON_TYPE_NONE
        })

        this._makeLogoutButton()
        this._nextPath = null

        Auth.whenFinalAccessLevelReady.then(function (level) {
            let nextPath = this.popNextPath()
            if (nextPath) {
                logger.debug(`navigating to next path "/${nextPath.join('/')}"`)
                Navigation.navigate(nextPath)
            }
            else {
                return Sections.showHome()
            }

        }.bind(this))
    }

    preload() {
        /* Don't call super method because we don't want to wait for cache to be ready */
        return Auth.whenInitialAccessLevelReady
    }

    navigate(path) {
        /* Don't stay on login section if done with auth */
        if (Auth.whenFinalAccessLevelReady.isFulfilled()) {
            return Sections.getHome()
        }

        return this
    }

    setNextPath(path) {
        this._nextPath = path
    }

    popNextPath() {
        let path = this._nextPath
        this._nextPath = null

        return path
    }

    _makeLogoutButton() {
        let button = $('<div class="qui-base-button">' +
                           '<div class="qui-icon"></div>' +
                           '<span class="label"></span>' +
                       '</div>')

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
            Window.reload()
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
