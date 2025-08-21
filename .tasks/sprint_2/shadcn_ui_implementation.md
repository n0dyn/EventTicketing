# shadcn/ui Implementation Guide

## Overview
This document outlines the steps needed to properly set up and implement shadcn/ui components in the EventTicketing frontend.

## What is shadcn/ui?
shadcn/ui is a collection of reusable components built using Radix UI and styled with Tailwind CSS. These components are not installed as a package but rather copied into the project, allowing for full customization.

## Installation Steps

### Step 1: Set Up the Required Base
```bash
# Add shadcn/ui CLI tool
npm install -D @shadcn/ui
```

### Step 2: Initialize shadcn/ui in the Project
```bash
# Run the init command to set up configuration
npx shadcn-ui init
```

This will ask you some questions:
- Choose a style (Default or New York)
- Select the location of your global CSS file
- Where to create the components
- Choose a color scheme
- Add the import alias for components

### Step 3: Add Required Components
Based on the code review, the following components are needed:

```bash
# Add the base components
npx shadcn-ui add button
npx shadcn-ui add dialog
npx shadcn-ui add input
npx shadcn-ui add form
npx shadcn-ui add textarea
npx shadcn-ui add switch
npx shadcn-ui add toast
npx shadcn-ui add label
npx shadcn-ui add card
npx shadcn-ui add table
npx shadcn-ui add badge
npx shadcn-ui add tabs
npx shadcn-ui add select
npx shadcn-ui add checkbox
```

## Component Structure

After installation, the following directory structure will be created:

```
src/components/ui/
├── button.tsx
├── dialog.tsx
├── input.tsx
├── form.tsx
├── textarea.tsx
├── switch.tsx
├── toast.tsx
└── ...
```

## Using Components in the Project

The existing code already references these components with imports like:

```tsx
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
// etc.
```

Once the components are properly installed, these imports will resolve correctly.

## Updating Existing Components

The following components need to be updated to use shadcn/ui:

1. **TicketTypeFormModal.tsx**
2. **PriceTiersTable.tsx**
3. **PromoCodesTable.tsx**
4. **Ticket management pages**

## Integration with Tailwind CSS

shadcn/ui uses Tailwind CSS. The project already has Tailwind CSS set up with the following plugins:
- @tailwindcss/forms
- @tailwindcss/typography
- @tailwindcss/aspect-ratio

The utilities `clsx` and `tailwind-merge` are also already installed, which are used by shadcn/ui's `cn` utility function.

## Testing Components

After installing the components, run the development server to ensure everything works:

```bash
npm run dev
```

Check for any styling issues or import errors in the browser console.

## Best Practices

1. **Customization**: Modify the components directly as needed, as they are part of your project's codebase.
2. **Consistency**: Use the provided components consistently throughout the application.
3. **Theme**: Use the theme variables in `globals.css` to maintain consistent styling.
4. **Forms**: Use the Form components with react-hook-form as shown in existing components. 