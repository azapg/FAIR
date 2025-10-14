export const camelCase = (str: string) => str.replace(/(_\w)/g, (m) => m[1].toUpperCase());
export const snakeCase = (str: string) => str.replace(/[A-Z]/g, (m) => `_${m.toLowerCase()}`);

export const toCamelCase = (obj: any): any => {
    if (Array.isArray(obj)) {
        return obj.map(v => toCamelCase(v));
    } else if (typeof obj === "object" && obj !== null) {
        const newObj: Record<string, any> = {};
        for (const key in obj) {
            newObj[camelCase(key)] = toCamelCase(obj[key]);
        }
        return newObj;
    }
    return obj;
};