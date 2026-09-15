/**
 * @namespace qtoggle.constants
 */


/**
 * A common debouncing delay interval, in milliseconds.
 * @alias qtoggle.constants.COMMON_DEBOUNCE_DELAY
 * @type {Number}
 */
export const COMMON_DEBOUNCE_DELAY = 1000

/**
 * The longest a debounced UI update may be postponed, however long the stream of events driving it lasts. Without a
 * bound, each event pushes the update back by the full delay, so a device that reports faster than once a second holds
 * the list at its old contents for as long as it keeps talking -- which reads as a frozen UI rather than a slow one.
 * @alias qtoggle.constants.COMMON_DEBOUNCE_MAX_WAIT
 * @type {Number}
 */
export const COMMON_DEBOUNCE_MAX_WAIT = 3000
