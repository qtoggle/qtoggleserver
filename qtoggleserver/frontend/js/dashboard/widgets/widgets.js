/**
 * @namespace qtoggle.dashboard.widgets
 */

export {STATE_ERROR}    from '$qui/views/view.js'
export {STATE_NORMAL}   from '$qui/views/view.js'
export {STATE_PROGRESS} from '$qui/views/view.js'


/* Following constants are expressed as fraction of cell width (em) */

/**
 * @alias qtoggle.dashboard.widgets.CELL_SPACING
 * @type {Number}
 */
export const CELL_SPACING = 0.05

/**
 * @alias qtoggle.dashboard.widgets.CELL_PADDING
 * @type {Number}
 */
export const CELL_PADDING = 0.05

/**
 * @alias qtoggle.dashboard.widgets.LABEL_HEIGHT
 * @type {Number}
 */
export const LABEL_HEIGHT = 0.2

/**
 * @alias qtoggle.dashboard.widgets.LABEL_HEIGHT_WITH_FRAME
 * @type {Number}
 */
export const LABEL_HEIGHT_WITH_FRAME = 0.25

/**
 * @alias qtoggle.dashboard.widgets.BEZEL_WIDTH
 * @type {Number}
 */
export const BEZEL_WIDTH = 0.025

/**
 * @alias qtoggle.dashboard.widgets.LABEL_FONT_SIZE
 * @type {Number}
 */
export const LABEL_FONT_SIZE = 0.13

/**
 * @alias qtoggle.dashboard.widgets.STATE_INVALID
 * @type {String}
 */
export const STATE_INVALID = 'invalid'

let registry = []


/**
 * Register a widget class.
 * @alias qtoggle.dashboard.widgets.register
 * @param {typeof qtoggle.dashboard.widgets.Widget} cls
 */
export function register(cls) {
    let categoryInfo = registry.find(c => c.name === cls.category)

    if (!categoryInfo) {
        categoryInfo = {
            name: cls.category,
            widgetClasses: []
        }
        registry.push(categoryInfo)
    }

    categoryInfo.widgetClasses.push(cls)
}

/**
 * Look up a widget class by type name.
 * @alias qtoggle.dashboard.widgets.find
 * @param {String} typeName
 * @returns {typeof qtoggle.dashboard.widgets.Widget}
 */
export function find(typeName) {
    let cls = null
    registry.find(function (categoryInfo) {
        cls = categoryInfo.widgetClasses.find(function (cls) {
            return cls.typeName === typeName
        })

        if (cls) {
            return true
        }
    })

    return cls
}

/**
 * Return the current widget registry.
 * @alias qtoggle.dashboard.widgets.getRegistry
 * @returns {Object[]}
 */
export function getRegistry() {
    return registry.slice()
}
