/**
 * @namespace qtoggle.dashboard.widgets
 */

export {STATE_ERROR}    from '$qui/views/view.js'
export {STATE_NORMAL}   from '$qui/views/view.js'
export {STATE_PROGRESS} from '$qui/views/view.js'


/* Following constants are expressed as fraction of cell width (em) */
export const CELL_SPACING = 0.05
export const CELL_PADDING = 0.05
export const LABEL_HEIGHT = 0.2
export const BEZEL_WIDTH = 0.025
export const LABEL_FONT_SIZE = 0.13

export const STATE_INVALID = 'invalid'

let registry = []


/**
 * @param {Function} cls
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
 * @param {String} typeName
 * @returns {?Function}
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
 * @returns {Object[]}
 */
export function getRegistry() {
    return registry.slice()
}
