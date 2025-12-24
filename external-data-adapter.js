/**
 * External Data Adapter Module
 * 
 * Function: Provides a data injection interface for external programs to forward external data to the project's internal core processing module.
 * Design Principles: Minimal intrusiveness; does not modify the original project's core logic; serves only as a data forwarding and format adaptation layer.
 * 
 * @module external-data-adapter
 * @version 1.0.0
 * @author AI Assistant
 * @date 2025-10-05
 */

import { executeTableEditActions, getTableEditTag, updateSheetsView } from './index.js';
import { BASE, USER } from './core/manager.js';

/**
 * Adapter State
 */
const adapterState = {
    initialized: false,
    lastError: null,
    operationCount: 0,
    debugMode: false
};

/**
 * Logging Utilities
 */
const logger = {
    info: (message, ...args) => {
        console.log(`[ExternalDataAdapter] ${message}`, ...args);
    },
    warn: (message, ...args) => {
        console.warn(`[ExternalDataAdapter] ⚠️ ${message}`, ...args);
    },
    error: (message, ...args) => {
        console.error(`[ExternalDataAdapter] ❌ ${message}`, ...args);
        adapterState.lastError = { message, timestamp: new Date(), args };
    },
    debug: (message, ...args) => {
        if (adapterState.debugMode) {
            console.log(`[ExternalDataAdapter] 🔍 ${message}`, ...args);
        }
    }
};

/**
 * Data Validator
 */
const validator = {
    /**
     * Verify if tables exist
     */
    checkTablesExist() {
        try {
            const sheets = BASE.getChatSheets();
            if (!sheets || sheets.length === 0) {
                return { valid: false, error: 'No tables found. Please create a table in the chat first.' };
            }
            const enabledSheets = sheets.filter(sheet => sheet.enable);
            if (enabledSheets.length === 0) {
                return { valid: false, error: 'No enabled tables found. Please enable at least one table.' };
            }
            return { valid: true, sheets: enabledSheets };
        } catch (error) {
            return { valid: false, error: `Table check failed: ${error.message}` };
        }
    },

    /**
     * Validate tableEdit command format
     */
    validateTableEditString(editString) {
        if (typeof editString !== 'string' || !editString.trim()) {
            return { valid: false, error: 'Edit command must be a non-empty string' };
        }

        // Check if it contains valid operation functions
        const validOperations = ['insertRow', 'updateRow', 'deleteRow'];
        const hasValidOperation = validOperations.some(op => editString.includes(op));
        
        if (!hasValidOperation) {
            return { valid: false, error: `Edit command must contain one of the following operations: ${validOperations.join(', ')}` };
        }

        return { valid: true };
    },

    /**
     * Validate JSON operation object
     */
    validateJsonOperation(operation) {
        if (!operation || typeof operation !== 'object') {
            return { valid: false, error: 'Operation must be an object' };
        }

        const { type, tableIndex } = operation;

        if (!['insert', 'update', 'delete'].includes(type)) {
            return { valid: false, error: `Invalid operation type: ${type}` };
        }

        if (typeof tableIndex !== 'number' || tableIndex < 0) {
            return { valid: false, error: `Invalid table index: ${tableIndex}` };
        }

        if (type === 'insert' && !operation.data) {
            return { valid: false, error: 'insert operation must contain a data field' };
        }

        if (type === 'update' && (!operation.data || typeof operation.rowIndex !== 'number')) {
            return { valid: false, error: 'update operation must contain data and rowIndex fields' };
        }

        if (type === 'delete' && typeof operation.rowIndex !== 'number') {
            return { valid: false, error: 'delete operation must contain a rowIndex field' };
        }

        return { valid: true };
    }
};

/**
 * Format Converter
 */
const converter = {
    /**
     * Extract edit commands from XML format
     * @param {string} xmlString - XML string containing <tableEdit> tags
     * @returns {string[]} Array of edit commands
     */
    extractFromXml(xmlString) {
        logger.debug('Extracting XML format data', xmlString);
        const { matches } = getTableEditTag(xmlString);
        logger.debug('Extraction result', matches);
        return matches;
    },

    /**
     * Convert JSON operation object to tableEdit command string
     * @param {Object} operation - Operation object
     * @returns {string} tableEdit command string
     */
    jsonToTableEditString(operation) {
        const { type, tableIndex, rowIndex, data } = operation;

        switch (type) {
            case 'insert':
                return `insertRow(${tableIndex}, ${JSON.stringify(data)})`;
            
            case 'update':
                return `updateRow(${tableIndex}, ${rowIndex}, ${JSON.stringify(data)})`;
            
            case 'delete':
                return `deleteRow(${tableIndex}, ${rowIndex})`;
            
            default:
                throw new Error(`Unknown operation type: ${type}`);
        }
    },

    /**
     * Convert JSON operation array to matches array
     * @param {Object[]} operations - Array of operation objects
     * @returns {string[]} Array of matches
     */
    jsonArrayToMatches(operations) {
        logger.debug('Converting JSON operation array', operations);
        
        const instructions = operations.map(op => {
            const validation = validator.validateJsonOperation(op);
            if (!validation.valid) {
                throw new Error(validation.error);
            }
            return this.jsonToTableEditString(op);
        });

        const combinedString = '<!--\n' + instructions.join('\n') + '\n-->';
        logger.debug('Generated command string', combinedString);
        
        return [combinedString];
    }
};

/**
 * Core Adapter Functions
 */
const adapter = {
    /**
     * Process XML format tableEdit data
     * @param {string} xmlString - XML string containing <tableEdit> tags
     * @returns {Promise<Object>} Processing result {success, message, data}
     */
    async processXmlData(xmlString) {
        logger.info('Processing XML format data');

        try {
            // Verify tables exist
            const tableCheck = validator.checkTablesExist();
            if (!tableCheck.valid) {
                return { success: false, message: tableCheck.error };
            }

            // Validate data format
            const validation = validator.validateTableEditString(xmlString);
            if (!validation.valid) {
                return { success: false, message: validation.error };
            }

            // Extract edit commands
            const matches = converter.extractFromXml(xmlString);
            if (!matches || matches.length === 0) {
                return { success: false, message: 'Failed to extract valid edit commands from XML' };
            }

            // Execute operations
            const result = executeTableEditActions(matches, null);

            if (result) {
                // Critical Fix 1: Save chat data to file to ensure data persistence
                try {
                    USER.saveChat();
                    logger.debug('Chat data saved to file');
                } catch (saveError) {
                    logger.warn('Failed to save chat data', saveError);
                }

                // Critical Fix 2: Refresh table view to ensure UI update
                try {
                    await updateSheetsView();
                    logger.debug('Table view refreshed');
                } catch (viewError) {
                    logger.warn('Failed to refresh table view', viewError);
                }

                adapterState.operationCount++;
                logger.info(`✅ Operation executed successfully (Total: ${adapterState.operationCount})`);
                return {
                    success: true,
                    message: 'Data processed successfully',
                    data: {
                        operationsExecuted: matches.length,
                        totalOperations: adapterState.operationCount
                    }
                };
            } else {
                return { success: false, message: 'Failed to execute table edit operations, please check console logs' };
            }

        } catch (error) {
            logger.error('Error occurred while processing XML data', error);
            return { success: false, message: `Error: ${error.message}`, error };
        }
    },

    /**
     * Process JSON format operation data
     * @param {Object|Object[]} jsonData - JSON operation object or array
     * @returns {Promise<Object>} Processing result {success, message, data}
     */
    async processJsonData(jsonData) {
        logger.info('Processing JSON format data');

        try {
            // Verify tables exist
            const tableCheck = validator.checkTablesExist();
            if (!tableCheck.valid) {
                return { success: false, message: tableCheck.error };
            }

            // Normalize to array
            const operations = Array.isArray(jsonData) ? jsonData : 
                              (jsonData.operations ? jsonData.operations : [jsonData]);

            if (operations.length === 0) {
                return { success: false, message: 'Operation array is empty' };
            }

            // Convert to matches format
            const matches = converter.jsonArrayToMatches(operations);

            // Execute operations
            const result = executeTableEditActions(matches, null);

            if (result) {
                // Critical Fix 1: Save chat data to file to ensure data persistence
                try {
                    USER.saveChat();
                    logger.debug('Chat data saved to file');
                } catch (saveError) {
                    logger.warn('Failed to save chat data', saveError);
                }

                // Critical Fix 2: Refresh table view to ensure UI update
                try {
                    await updateSheetsView();
                    logger.debug('Table view refreshed');
                } catch (viewError) {
                    logger.warn('Failed to refresh table view', viewError);
                }

                adapterState.operationCount++;
                logger.info(`✅ Operation executed successfully (Total: ${adapterState.operationCount})`);
                return {
                    success: true,
                    message: 'Data processed successfully',
                    data: {
                        operationsExecuted: operations.length,
                        totalOperations: adapterState.operationCount
                    }
                };
            } else {
                return { success: false, message: 'Failed to execute table edit operations, please check console logs' };
            }

        } catch (error) {
            logger.error('Error occurred while processing JSON data', error);
            return { success: false, message: `Error: ${error.message}`, error };
        }
    },

    /**
     * Auto-detect format and process data
     * @param {string|Object} data - Input data (XML string or JSON object)
     * @returns {Promise<Object>} Processing result
     */
    async processData(data) {
        if (typeof data === 'string') {
            return await this.processXmlData(data);
        } else if (typeof data === 'object') {
            return await this.processJsonData(data);
        } else {
            return { success: false, message: 'Unsupported data type. Please provide an XML string or JSON object.' };
        }
    }
};

/**
 * Initialize External Data Adapter
 * @param {Object} options - Configuration options
 * @param {boolean} options.debugMode - Whether to enable debug mode
 */
export function initExternalDataAdapter(options = {}) {
    if (adapterState.initialized) {
        logger.warn('Adapter is already initialized');
        return;
    }

    adapterState.debugMode = options.debugMode || false;
    adapterState.initialized = true;

    logger.info('External Data Adapter initialized successfully');
    logger.info(`Debug Mode: ${adapterState.debugMode ? 'ON' : 'OFF'}`);

    // Expose adapter interface to the global scope
    if (typeof window !== 'undefined') {
        window.externalDataAdapter = {
            processXmlData: adapter.processXmlData.bind(adapter),
            processJsonData: adapter.processJsonData.bind(adapter),
            processData: adapter.processData.bind(adapter),
            getState: () => ({ ...adapterState }),
            setDebugMode: (enabled) => { adapterState.debugMode = enabled; },
            getLastError: () => adapterState.lastError
        };
        logger.info('Adapter interface exposed to window.externalDataAdapter');
    }
}

/**
 * Export adapter interface (for Node.js environment or module imports)
 */
export const externalDataAdapter = {
    processXmlData: adapter.processXmlData.bind(adapter),
    processJsonData: adapter.processJsonData.bind(adapter),
    processData: adapter.processData.bind(adapter),
    getState: () => ({ ...adapterState }),
    setDebugMode: (enabled) => { adapterState.debugMode = enabled; },
    getLastError: () => adapterState.lastError
};

export default externalDataAdapter;

