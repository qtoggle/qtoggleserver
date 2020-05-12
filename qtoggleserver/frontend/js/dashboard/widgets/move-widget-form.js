
import Logger from '$qui/lib/logger.module.js'

import {gettext}        from '$qui/base/i18n.js'
import {ComboField}     from '$qui/forms/common-fields.js'
import {PageForm}       from '$qui/forms/common-forms.js'
import FormButton       from '$qui/forms/form-button.js'
import * as ArrayUtils  from '$qui/utils/array.js'
import * as StringUtils from '$qui/utils/string.js'

import * as Dashboard     from '../dashboard.js'


const logger = Logger.get('qtoggle.dashboard.widgets')


class PanelPickerField extends ComboField {

    constructor({dashboardWidget, ...args}) {
        super({...args})

        this._dashboardWidget = dashboardWidget
    }

    makeChoices() {
        let choices = Object.values(Dashboard.getAllPanels()).map(function (panel) {

            return {
                label: this._makeLabel(panel),
                value: panel.getId()
            }

        }, this)

        let thisPanel = this._dashboardWidget.getPanel()
        choices = choices.filter(c => c.value !== thisPanel.getId())

        return ArrayUtils.sortKey(choices, choice => choice.label)
    }

    _makeLabel(panel) {
        return panel.getPath().join(' &#x025B8; ')
    }

}


/**
 * @alias qtoggle.dashboard.widgets.MoveWidgetForm
 * @extends qui.forms.commonforms.PageForm
 */
class MoveWidgetForm extends PageForm {

    /**
     * @constructs
     * @param {qtoggle.dashboard.widgets.Widget} widget
     */
    constructor(widget) {
        let title = StringUtils.formatPercent(
            gettext('Move %(widget)s to another panel'),
            {widget: widget.toString()}
        )

        super({
            icon: Dashboard.PANEL_ICON,
            title: title,
            pathId: 'move',
            modal: true,

            fields: [
                new PanelPickerField({
                    name: 'panel',
                    label: gettext('Panel'),
                    description: gettext('Select the destination panel.'),
                    required: true,
                    dashboardWidget: widget
                })
            ],
            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true}),
                new FormButton({id: 'ok', caption: gettext('OK'), def: true})
            ]
        })

        this._widget = widget
    }

    applyData(data) {
        let panels = Dashboard.getAllPanels()
        let panel = panels.find(p => p.getId() === data.panel)
        if (!panel) {
            logger.error(`cannot find panel with id ${data.panel}`)
            return
        }

        this._widget.moveToPanel(panel)
    }

}


export default MoveWidgetForm
