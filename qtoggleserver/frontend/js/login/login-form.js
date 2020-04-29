
import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {PasswordField}   from '$qui/forms/common-fields.js'
import {TextField}       from '$qui/forms/common-fields.js'
import {PageForm}        from '$qui/forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import {ValidationError} from '$qui/forms/forms.js'

import * as AuthAPI from '$app/api/auth.js'
import * as Auth    from '$app/auth.js'

import * as Login from './login.js'


const logger = Login.logger


/**
 * @alias qtoggle.login.LoginForm
 * @extends qui.forms.PageForm
 */
class LoginForm extends PageForm {

    /**
     * @constructs
     */
    constructor() {
        super({
            title: gettext('Login'),
            icon: Login.KEY_ICON,
            modal: true,
            compact: true,
            fields: [
                new TextField({
                    name: 'username',
                    placeholder: gettext('Username'),
                    required: true,
                    autocomplete: 'username'
                }),
                new PasswordField({
                    name: 'password',
                    placeholder: gettext('Password'),
                    autocomplete: true
                }),
                new CheckField({
                    name: 'rememberMe',
                    label: gettext('Remember Me')
                })
            ],
            buttons: [
                new FormButton({id: 'login', caption: gettext('Login'), def: true, style: 'interactive'})
            ]
        })
    }

    validate(data) {
        logger.debug('validating credentials')

        return Auth.login(data.username, data.password).then(function (level) {
            if (level <= AuthAPI.ACCESS_LEVEL_NONE) {
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
