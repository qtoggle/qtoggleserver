/**
 * @namespace qtoggle.api.attrdeffields
 */

import {gettext}     from '$qui/base/i18n.js'
import {LabelsField} from '$qui/forms/common-fields/common-fields.js'
import * as Theme    from '$qui/theme.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


/**
 * @alias qtoggle.api.attrfields.WiFiSignalStrengthField
 * @extends qui.forms.commonfields.ProgressDiskField
 */
export class WiFiSignalStrengthField extends LabelsField {

    valueToWidget(value) {
        value = Math.min(3, Math.max(0, value))

        let backgrounds = { // TODO es7 class fields
            0: '@red-color',
            1: '@orange-color',
            2: '@yellow-color',
            3: '@green-color'
        }

        let labels = { // TODO es7 class fields
            0: gettext('weak'),
            1: gettext('fair'),
            2: gettext('good'),
            3: gettext('excellent')
        }

        let background = Theme.getColor(backgrounds[value])
        let label = labels[value]
        let text = `${label} (${value}/3)`

        super.valueToWidget([{text, background}])
    }

}
