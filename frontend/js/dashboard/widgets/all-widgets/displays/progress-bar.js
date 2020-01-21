
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm, AnalogWidget} from '../analog-widget.js'


export class ConfigForm extends AnalogWidgetConfigForm {

    constructor(widget) {
        super(widget, {readonly: true})
    }

}


class ProgressBar extends AnalogWidget {

    constructor() {
        super({readonly: true})
    }

}

// TODO es7 class fields
ProgressBar.category = gettext('Displays')
ProgressBar.displayName = gettext('Progress Bar')
ProgressBar.typeName = 'ProgressBar'
ProgressBar.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
ProgressBar.ConfigForm = ConfigForm
ProgressBar.vResizable = true
ProgressBar.hResizable = true
ProgressBar.width = 2


Widgets.register(ProgressBar)


export default ProgressBar
