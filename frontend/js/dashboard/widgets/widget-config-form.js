
import {gettext}        from '$qui/base/i18n.js'
import {TextField}      from '$qui/forms/common-fields.js'
import {PageForm}       from '$qui/forms/common-forms.js'
import FormButton       from '$qui/forms/form-button.js'
import * as ObjectUtils from '$qui/utils/object.js'
import * as Window      from '$qui/window.js'

import * as Cache from '$app/cache.js'

import * as Dashboard  from '../dashboard.js'
import PortPickerField from './port-picker-field.js'
import * as Widgets    from './widgets.js'


/**
 * @class QToggle.DashboardSection.Widgets.WidgetConfigForm
 * @extends qui.forms.PageForm
 * @param {QToggle.DashboardSection.Widgets.Widget} widget
 * @param {Object} attributes
 */
class WidgetConfigForm extends PageForm {

    constructor(widget, {...params} = {}) {
        let defaultFields = [
            new TextField({
                name: 'label',
                label: gettext('Label'),
                maxLength: 128
            })
        ]

        params.fields = defaultFields.concat(params.fields || [])

        ObjectUtils.assignDefault(params, {
            title: widget.constructor.displayName,
            largeTop: true,
            closable: true,
            transparent: false,
            fieldsAlignment: 'sides',
            column: true,
            pathId: widget.getId(),
            keepPrevVisible: true,
            compact: true,
            width: 'auto',
            continuousValidation: true,
            buttons: [
                new FormButton({id: 'done', caption: gettext('Done'), def: true})
            ]
        })

        super(params)

        this._widget = widget
    }

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

        Dashboard.savePanels()
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

    getWidget() {
        return this._widget
    }

    /**
     * @param {QToggle.DashboardSection.Widgets.Widget} widget
     * @returns {Object}
     */
    fromWidget(widget) {
        let data = widget.configToJSON()
        data.label = widget.getLabel()

        return data
    }

    /**
     * @param {Object} data
     * @param {QToggle.DashboardSection.Widgets.Widget} widget
     */
    toWidget(data, widget) {
        widget.setLabel(data.label)
        widget.configFromJSON(data)
    }

    /**
     * @param {Object} port
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

    updatePorts() {
        this.getFields().forEach(function (field) {
            if (field instanceof PortPickerField) {
                field.updateChoices()
            }
        })
    }

    /**
     * Returns the cached attributes of a port.
     * @param {String} portId the id of the port whose attributes will be returned
     * @returns {?Object}
     */
    getPort(portId) {
        return Cache.getPort(portId)
    }

    navigate(pathId) {
        switch (pathId) {
            case 'remove':
                return this._widget.makeRemoveForm()
        }
    }

}


export default WidgetConfigForm
