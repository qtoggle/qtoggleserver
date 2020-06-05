
import {gettext}         from '$qui/base/i18n.js'
import {CompositeField}  from '$qui/forms/common-fields/common-fields.js'
import {PushButtonField} from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import {PageForm}        from '$qui/forms/common-forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as Window       from '$qui/window.js'

import * as Cache from '$app/cache.js'

import PortPickerField from './port-picker-field.js'
import * as Widgets    from './widgets.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


/**
 * @alias qtoggle.dashboard.widgets.WidgetConfigForm
 * @extends qui.forms.commonforms.PageForm
 */
class WidgetConfigForm extends PageForm {

    /**
     * @constructs
     * @param {qtoggle.dashboard.widgets.Widget} widget
     * @param {...*} args parent class parameters
     */
    constructor({widget, ...args}) {
        let defaultStartFields = [
            new TextField({
                name: 'label',
                label: gettext('Label'),
                maxLength: 128
            })
        ]

        let defaultEndFields = [
            new CompositeField({
                name: 'action_buttons',
                label: gettext('Actions'),
                separator: true,
                flow: 'vertical',
                fields: [
                    new PushButtonField({
                        name: 'move',
                        caption: gettext('Move'),
                        style: 'interactive',
                        onClick(form) {
                            form.pushPage(form.getWidget().makeMoveForm())
                        }
                    }),
                    new PushButtonField({
                        name: 'remove',
                        caption: gettext('Remove'),
                        style: 'danger',
                        onClick(form) {
                            form.pushPage(form.getWidget().makeRemoveForm())
                        }
                    })
                    // new PushButtonField({
                    //     name: 'replace',
                    //     style: 'interactive',
                    //     caption: gettext('Replace'),
                    //     onClick(form) {
                    //         form.pushPage(form.getWidget().makeReplaceForm())
                    //     }
                    // })
                ]
            })
        ]

        args.fields = [...defaultStartFields, ...(args.fields || []), ...defaultEndFields]

        ObjectUtils.assignDefault(args, {
            title: widget.constructor.displayName,
            largeTop: true,
            closable: true,
            transparent: false,
            columnLayout: true,
            pathId: widget.getId(),
            keepPrevVisible: true,
            compact: true,
            width: 'auto',
            continuousValidation: true,
            buttons: [
                new FormButton({id: 'done', caption: gettext('Done'), style: 'interactive'})
            ]
        })

        super(args)

        this._widget = widget
    }

    /**
     * Update config form data from widget.
     */
    updateFromWidget() {
        this.setData(this.fromWidget(this._widget))

        this.onUpdateFromWidget()

        /* We need to call setData + validate again, since onUpdateFromWidget() could add new fields */
        this.setData(this.fromWidget(this._widget))
    }

    onChange(data, fieldName) {
        let field = this.getField(fieldName)

        /* Whenever the port is changed, call fromPort() and update form fields accordingly */
        if (field instanceof PortPickerField) {
            let portId = data[fieldName]
            let port = this.getPort(portId)
            if (port) {
                let dataFromPort = this.fromPort(port, fieldName)
                if (Object.keys(dataFromPort).length) {
                    this.setData(dataFromPort)
                }

                ObjectUtils.forEach(dataFromPort, function (name, value) {
                    let field = this.getField(name)
                    if (field) {
                        field.onChange(value, this)
                    }
                }, this)
            }
        }
    }

    onChangeValid(data, fieldName) {
        let oldState = this._widget.getState()

        this.toWidget(data, this._widget)
        this._widget.refreshContent()
        this._widget.updateState()

        /* UpdateState() calls showCurrentValue() itself upon transition, but here we need it called even if there
         * hasn't been any transition */
        if (this._widget.getState() === oldState === Widgets.STATE_NORMAL) {
            this._widget.showCurrentValue()
        }

        this._widget.getPanel().save()
    }

    onClose() {
        if (this._widget._configForm !== this) {
            return
        }

        if (this._widget.getPanel().getSelectedWidget() === this._widget && !Window.isSmallScreen()) {
            /* On large screens, we need to completely deselect the current widget upon config form close */
            this._widget.getPanel().setSelectedWidget(null)
            this._widget.getPanel().handleWidgetSelect(null)

            /* Also open the panel options bar */
            if (this.getContext().isCurrent()) {
                this._widget.getPanel().openOptionsBar()
            }
        }
    }

    onButtonPress(button) {
        switch (button.getId()) {
            case 'done':
                this.close(/* force = */ true)
                break
        }
    }

    /**
     * @returns {qtoggle.dashboard.widgets.Widget}
     */
    getWidget() {
        return this._widget
    }

    /**
     * Adapt widget data to form data.
     * @param {qtoggle.dashboard.widgets.Widget} widget
     * @returns {Object}
     */
    fromWidget(widget) {
        let data = widget.configToJSON()
        data.label = widget.getLabel()

        return data
    }

    /**
     * Adapt form data to widget data.
     * @param {Object} data
     * @param {qtoggle.dashboard.widgets.Widget} widget
     */
    toWidget(data, widget) {
        widget.setLabel(data.label)
        widget.configFromJSON(data)
    }

    /**
     * Extract form data from a selected port. By default extracts only port label.
     * @param {Object} port
     * @param {String} fieldName corresponding port form field name
     */
    fromPort(port, fieldName) {
        return {
            label: port.display_name || port.id
        }
    }

    /**
     * Called after form data is updated from widget.
     */
    onUpdateFromWidget() {
    }

    /**
     * Update all fields of type {@link qtoggle.dashboard.widgets.PortPickerField}.
     */
    updatePortFields() {
        this.getFields().forEach(function (field) {
            if (field instanceof PortPickerField) {
                field.updateChoices()
            }
        })
    }

    /**
     * Return the cached attributes of a port.
     * @param {String} portId the port id
     * @returns {?Object}
     */
    getPort(portId) {
        return Cache.getPort(portId)
    }

    navigate(pathId) {
        switch (pathId) {
            case 'remove':
                return this._widget.makeRemoveForm()

            case 'move':
                return this._widget.makeMoveForm()

            // case 'replace':
            //     return this._widget.makeReplaceForm()
        }
    }

}


export default WidgetConfigForm
