export function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-300">
      <div className="max-w-[65%] rounded-[16px_16px_4px_16px] bg-user-bubble px-5 py-4 text-sm leading-7 text-foreground shadow-sm">{content}</div>
    </div>
  )
}
