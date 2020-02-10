
import {gettext}            from '$qui/base/i18n.js'
import {Mixin}              from '$qui/base/mixwith.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as StringUtils     from '$qui/utils/string.js'

import * as Utils from '$app/utils.js'

import * as Dashboard from './dashboard.js'


const logger = Dashboard.logger


/** @lends qtoggle.dashboard.PanelGroupCompositeMixin */
const PanelGroupCompositeMixin = Mixin((superclass = Object) => {

    /**
     * @alias qtoggle.dashboard.PanelGroupCompositeMixin
     * @mixin
     */
    return class PanelGroupCompositeMixin extends superclass {

        /**
         * @constructs
         * @param {String} [name]
         * @param {?qtoggle.dashboard.Group} [parent]
         * @param {...*} args
         */
        constructor({name = '', parent = null, ...args} = {}) {
            super(args)

            this._name = name
            this._parent = parent
        }

        toString() {
            return this._name
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
         * @returns {?qtoggle.dashboard.Group}
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
         * @returns {qtoggle.dashboard.PanelGroupCompositeMixin[]}
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
         * Serialize to a JSON object.
         * @returns {Object}
         */
        toJSON() {
            return {
                name: this._name
            }
        }

        /**
         * Load from a serialized JSON object.
         * @param {Object} json
         */
        fromJSON(json) {
            if (json.name != null) {
                this._name = json.name
            }
        }

        /**
         * Mark for saving.
         */
        save() {
            Dashboard.savePanels()
        }

        /**
         * Update view UI elements.
         */
        updateUI() {
        }

        /**
         * @returns {qui.pages.PageMixin}
         */
        makeRemoveForm() {
            let msg = StringUtils.formatPercent(
                gettext('Really remove %(object)s?'),
                {object: Messages.wrapLabel(this.toString())}
            )

            return new ConfirmMessageForm({
                message: msg,
                onYes: function () {
                    logger.debug(`removing "${this.getPathStr()}"`)
                    let parent = this.getParent()
                    parent.removeChild(this)
                    parent.save()
                    this.close()
                }.bind(this),
                pathId: 'remove'
            })
        }

    }

})


export default PanelGroupCompositeMixin
