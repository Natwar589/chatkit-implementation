#!/usr/bin/env node
/**
 * Setup script to help configure environment variables for the ChatKit frontend.
 */

import { readFileSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function setupEnvironment() {
    console.log("🔧 ChatKit Frontend Environment Setup");
    console.log("=" + "=".repeat(39));
    
    const envFile = join(__dirname, ".env");
    const envExampleFile = join(__dirname, ".env.example");
    
    // Check if .env exists
    if (existsSync(envFile)) {
        console.log(`✅ Found existing .env file at: ${envFile}`);
        try {
            const content = readFileSync(envFile, 'utf8');
            if (content.trim().length === 0) {
                console.log("⚠️  The .env file is empty.");
            } else {
                console.log("✅ The .env file has content.");
            }
        } catch (error) {
            console.log("❌ Could not read .env file");
        }
    } else {
        console.log("❌ No .env file found.");
        if (existsSync(envExampleFile)) {
            console.log("💡 You can copy from .env.example: cp .env.example .env");
        }
    }
    
    console.log("\n📋 Frontend Environment Variables (all optional):");
    console.log("1. VITE_CHATKIT_API_URL - ChatKit API endpoint (defaults to /chatkit)");
    console.log("2. VITE_FACTS_API_URL - Facts API endpoint (defaults to /facts)");
    console.log("3. VITE_CHATKIT_API_DOMAIN_KEY - Domain key for production");
    console.log("4. BACKEND_URL - Backend URL for Vite proxy (defaults to http://127.0.0.1:8001)");
    
    console.log("\n🔍 Current configuration:");
    
    // Check current environment variables
    const vars = [
        'VITE_CHATKIT_API_URL',
        'VITE_FACTS_API_URL', 
        'VITE_CHATKIT_API_DOMAIN_KEY',
        'BACKEND_URL'
    ];
    
    vars.forEach(varName => {
        const value = process.env[varName];
        if (value) {
            console.log(`✅ ${varName} is set: ${value}`);
        } else {
            console.log(`⚪ ${varName} is not set (will use default)`);
        }
    });
    
    console.log("\n📝 For local development:");
    console.log("   - No environment variables are required");
    console.log("   - The app uses sensible defaults and Vite proxy");
    console.log("   - Backend should be running on http://127.0.0.1:8001");
    
    console.log("\n📝 For production deployment:");
    console.log("   - Register your domain at: https://platform.openai.com/settings/organization/security/domain-allowlist");
    console.log("   - Set VITE_CHATKIT_API_DOMAIN_KEY to your actual domain key");
    console.log("   - Update allowedHosts in vite.config.ts");
    
    console.log("\n🚀 To start the frontend:");
    console.log("   npm install");
    console.log("   npm run dev");
}

setupEnvironment();
