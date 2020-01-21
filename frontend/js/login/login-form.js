
import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {PasswordField}   from '$qui/forms/common-fields.js'
import {TextField}       from '$qui/forms/common-fields.js'
import {PageForm}        from '$qui/forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import {ValidationError} from '$qui/forms/forms.js'

import * as API  from '$app/api.js'
import * as Auth from '$app/auth.js'

import * as Login from './login.js'


const logger = Login.logger


/**
 * @class QToggle.LoginSection.LoginForm
 * @param {Number} requiredLevel the required access level
 * @extends qui.forms.PageForm
 */
class LoginForm extends PageForm {

    constructor() {
        super({
            title: gettext('Login'),
            icon: Login.KEY_ICON,
            modal: true,
            compact: true,
            fields: [
                new TextField({
                    name: 'username',
                    label: gettext('Username'),
                    required: true,
                    autocomplete: 'username'
                }),
                new PasswordField({
                    name: 'password',
                    label: gettext('Password'),
                    autocomplete: true
                }),
                new CheckField({
                    name: 'rememberMe',
                    label: gettext('Remember Me')
                })
            ],
            buttons: [
                new FormButton({id: 'login', caption: gettext('Login'), def: true})
            ]
        })
    }

    validate(data) {
        logger.debug('validating credentials')

        return Auth.login(data.username, data.password).then(function (level) {
            if (level <= API.ACCESS_LEVEL_NONE) {
                throw new ValidationError(gettext('Login failed!'))
            }
        })
    }

    applyData(data) {
        logger.debug('authentication succeeded')

        if (data.rememberMe) {
            Auth.storeCredentials()
        }
    }

}


export default LoginForm
