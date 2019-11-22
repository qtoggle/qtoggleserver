import {gettext}            from '$qui/base/i18n.js'
import {Mixin}              from '$qui/base/mixwith.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as StringUtils     from '$qui/utils/string.js'

import * as Utils from '$app/utils.js'

import * as Dashboard from './dashboard.js'


const logger = Dashboard.logger


export default Mixin((superclass = Object) => {

    /**
     * @mixin QToggle.DashboardSection.PanelGroupCompositeMixin
     * @param {Object} attributes
     */
    return class PanelGroupCompositeMixin extends superclass {

        constructor({name = '', parent = null, ...params}) {
            super(params)

            this._name = name
            this._parent = parent
        }

        /**
         * @returns {String}
         */
        getName() {
            return this._name
        }

        /**
         * @param {String} name
         */
        setName(name) {
            this._name = name
            this.updateUI()
            if (this._parent) {
                this._parent.updateUI()
            }
        }

        /**
         * @returns {QToggle.DashboardSection.Group}
         */
        getParent() {
            return this._parent
        }

        /**
         * @returns {String}
         */
        getId() {
            return Utils.nameToId(this._name)
        }

        /**
         * @returns {QToggle.DashboardSection.PanelGroupCompositeMixin[]}
         */
        getPath() {
            if (!this._parent) {
                return [this]
            }

            return this._parent.getPath().concat([this])
        }

        /**
         * @returns {String}
         */
        getPathStr() {
            return this.getPath().map(c => c._name).join('/')
        }

        /**
         * @returns {Object}
         */
        toJSON() {
            return {
                name: this._name
            }
        }

        /**
         * @param {Object} json
         */
        fromJSON(json) {
            if (json.name != null) {
                this._name = json.name
            }
        }

        updateUI() {
        }

        makeRemoveForm() {
            let msg = StringUtils.formatPercent(
                gettext('Really remove %(object)s?'),
                {object: Messages.wrapLabel(this.getName())}
            )

            return ConfirmMessageForm.create(msg, /* onYes = */ function () {

                logger.debug(`removing "${this.getPathStr()}"`)
                this.getParent().removeChild(this)
                this.close()
                Dashboard.savePanels()

            }.bind(this), /* onNo = */ null, /* pathId = */ 'remove')
        }

    }

})
