
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm, AnalogWidget} from '../analog-widget.js'


class ConfigForm extends AnalogWidgetConfigForm {

    constructor({...args}) {
        super({readonly: true, ...args})
    }

}


/**
 * @alias qtoggle.dashboard.widgets.displays.ProgressBar
 * @extends qtoggle.dashboard.widgets.AnalogWidget
 */
class ProgressBar extends AnalogWidget {

    static category = gettext('Displays')
    static displayName = gettext('Progress Bar')
    static typeName = 'ProgressBar'
    static icon = new StockIcon({name: 'widget-progress-bar', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm
    static vResizable = true
    static hResizable = true
    static width = 2


    /**
     * @constructs
     */
    constructor() {
        super({readonly: true})
    }

}


Widgets.register(ProgressBar)


export default ProgressBar
