import {gettext}            from '$qui/base/i18n.js'
import {mix}                from '$qui/base/mixwith.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import StickyModalPageMixin from '$qui/messages/sticky-modal-page.js'
import * as ObjectUtils     from '$qui/utils/object.js'
import * as Window          from '$qui/window.js'


/**
 * A message box that prompts for updating to a new version.
 * @alias qtoggle.common.NewVersionMessageForm
 * @extends qui.messages.commonmessageforms.ConfirmMessageForm
 * @mixes qui.messages.StickyModalPageMixin
 * @param {Object} params
 * * see {@link qui.messages.commonmessageforms.ConfirmMessageForm} for confirm message form parameters
 * * see {@link qui.messages.StickyModalPageMixin} for sticky modal page parameters
 */
export default class NewVersionMessageForm extends mix(ConfirmMessageForm).with(StickyModalPageMixin) {

    constructor({...params} = {}) {
        let that
        let msg = gettext('A new app version has been installed. Refresh to update now?')

        ObjectUtils.setDefault(params, 'message', msg)
        ObjectUtils.setDefault(params, 'onYes', () => that.onYes())

        super(params)

        that = this
    }

    onYes() {
        Window.reload()
    }

}
