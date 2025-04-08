"use client"

import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-95 relative overflow-hidden group",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-md hover:shadow-primary/20 dark:hover:shadow-primary/30 active:animate-button-pop",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:shadow-md hover:shadow-destructive/20 dark:hover:shadow-destructive/30 active:animate-button-pop",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground hover:border-accent/50 hover:shadow-sm active:animate-button-pop",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 hover:shadow-md hover:shadow-secondary/20 dark:hover:shadow-secondary/30 active:animate-button-pop",
        ghost: "hover:bg-accent hover:text-accent-foreground active:animate-button-pop",
        link: "text-primary underline-offset-4 hover:underline active:animate-button-wiggle",
        glow: "bg-primary text-primary-foreground hover:bg-primary/90 animate-pulse-glow hover:animate-none active:animate-button-pop relative overflow-hidden bg-gradient-to-r from-primary via-primary/80 to-primary",
        shimmer: "bg-primary text-primary-foreground hover:bg-primary/90 relative overflow-hidden bg-[linear-gradient(110deg,#000103,45%,hsl(var(--primary)),55%,#000103)] bg-[length:200%_100%] animate-button-shimmer active:animate-button-pop",
        gradient: "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground hover:shadow-md hover:shadow-primary/20 active:animate-button-pop before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent before:translate-x-[-200%] hover:before:animate-shimmer",
        float: "bg-primary text-primary-foreground hover:shadow-lg hover:shadow-primary/30 hover:translate-y-[-3px] transition-all duration-300 hover:bg-primary/90 active:animate-button-pop",
        bounce: "bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-md hover:animate-bounce active:animate-button-pop",
        ripple: "bg-primary text-primary-foreground hover:bg-primary/90 active:animate-button-pop [&>span]:hover:animate-ripple",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
      animation: {
        none: "",
        pulse: "animate-pulse-glow",
        pop: "hover:animate-button-pop",
        wiggle: "hover:animate-button-wiggle",
        shimmer: "animate-button-shimmer",
        float: "hover:translate-y-[-3px] hover:shadow-lg transition-all duration-300",
        bounce: "hover:animate-bounce",
        expand: "hover:animate-expand",
        ripple: "",
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      animation: "none",
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, animation, asChild = false, children, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    
    // Create a ripple effect element for ripple animation variant
    const rippleContent = animation === "ripple" || variant === "ripple" ? (
      <>
        {children}
        <span className="absolute inset-0 pointer-events-none opacity-0 bg-white/30 rounded-full scale-0 transition-all duration-700" />
      </>
    ) : children;

    return (
      <Comp 
        className={cn(buttonVariants({ variant, size, animation, className }))} 
        ref={ref} 
        {...props} 
      >
        {rippleContent}
      </Comp>
    )
  },
)
Button.displayName = "Button"

export { Button, buttonVariants }
